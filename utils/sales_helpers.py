import asyncio
import logging
import pathlib
import uuid

import pandas as pd
from config.settings import create_genai_client, COLUMN_GROUPS, SalesReport
from google.genai.types import Part
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from utils.gemini_limits import (
    MAX_ATTEMPTS,
    get_gemini_coordinator,
    is_retryable,
    response_tokens,
    retry_delay,
)
from utils.helpers import find_pdfs
from utils.prompts import build_sales_extraction_prompt
from utils.sales_dates import format_long_dates, normalize_monthly_dates


LOGGER = logging.getLogger(__name__)
if not LOGGER.handlers:
    LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

MAX_JOB_CONCURRENCY = 6


async def extract_sales_data(pdf_path, client, job_id, position, total):
    coordinator = get_gemini_coordinator()
    contents = [
        Part.from_bytes(
            data=pathlib.Path(pdf_path).read_bytes(), mime_type="application/pdf"
        ),
        build_sales_extraction_prompt(),
    ]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        reservation = await coordinator.wait_for_reservation_async()
        actual_tokens = None
        wait = None
        LOGGER.info(
            "Sales job %s processing %d/%d: %s (attempt %d/%d)",
            job_id, position, total, pdf_path, attempt, MAX_ATTEMPTS,
        )
        try:
            response = await client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": SalesReport,
                },
            )
            actual_tokens = response_tokens(response)
            return response.parsed.model_dump()
        except Exception as error:
            if attempt == MAX_ATTEMPTS or not is_retryable(error):
                raise
            wait = retry_delay(error, attempt)
            LOGGER.warning(
                "Sales job %s retrying %s in %.1fs after %s",
                job_id, pdf_path, wait, error,
            )
        finally:
            coordinator.release(reservation, actual_tokens)
        await asyncio.sleep(wait)


async def _process_sales_files(pdf_files, sales_folder, progress_callback, job_id):
    rows = []
    completed = 0
    semaphore = asyncio.Semaphore(MAX_JOB_CONCURRENCY)
    base_client = create_genai_client()

    async def process(position, pdf_path):
        relative_path = str(pdf_path.relative_to(sales_folder))
        async with semaphore:
            try:
                row = await extract_sales_data(
                    pdf_path, base_client.aio, job_id, position, len(pdf_files)
                )
            except Exception as error:
                LOGGER.error(
                    "Sales job %s failed %d/%d: %s (%s)",
                    job_id, position, len(pdf_files), relative_path, error,
                )
                return relative_path, "failed", None
            LOGGER.info(
                "Sales job %s processed %d/%d: %s",
                job_id, position, len(pdf_files), relative_path,
            )
            return relative_path, "processed", row

    tasks = [
        asyncio.create_task(process(position, pdf_path))
        for position, pdf_path in enumerate(pdf_files, start=1)
    ]
    try:
        for task in asyncio.as_completed(tasks):
            name, status, row = await task
            completed += 1
            if row is not None:
                rows.append(row)
            if progress_callback:
                progress_callback(completed, len(pdf_files), name, status)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await base_client.aio.aclose()
        finally:
            base_client.close()
    return rows


def write_to_excel_with_categories(df: pd.DataFrame, output_excel: str):
    df["Date"] = normalize_monthly_dates(df["Date"])
    df.sort_values("Date", inplace=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly Report"

    all_fields = ["Date"]
    for fields in COLUMN_GROUPS.values():
        all_fields.extend(fields)
    all_fields.append("Notes")

    first_row = [""]  # Date column top
    merge_ranges = []
    col = 2
    for category, fields in COLUMN_GROUPS.items():
        first_row.extend([category] + [""] * (len(fields) - 1))
        merge_ranges.append((col, col + len(fields) - 1, category))
        col += len(fields)
    first_row.append("")

    ws.append(first_row)
    ws.append(all_fields)

    for row in df.itertuples(index=False):
        ws.append(list(row))

    # Keep dates as Excel values so they remain sortable and filterable while
    # displaying them in a readable long-date format.
    format_long_dates(ws)

    for start_col, end_col, category in merge_ranges:
        ws.merge_cells(f"{get_column_letter(start_col)}1:{get_column_letter(end_col)}1")
        cell = ws[f"{get_column_letter(start_col)}1"]
        cell.value = category
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

        fill_color = {
            "RETAIL SUPERMARKET & BUTCHERY": "FFD700",
            "DINER": "ADD8E6",
            "SHOPIFY": "98FB98",
            "SALES SUMMARY": "F08080"
        }.get(category, "DDDDDD")

        for col in range(start_col, end_col + 1):
            ws[f"{get_column_letter(col)}1"].fill = PatternFill(start_color=fill_color, fill_type="solid")

    for col in range(1, ws.max_column + 1):
        ws[f"{get_column_letter(col)}2"].font = Font(bold=True)
        ws[f"{get_column_letter(col)}2"].alignment = Alignment(horizontal="center")

    for col in ws.columns:
        max_len = max((len(str(cell.value)) for cell in col if cell.value), default=0)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max_len + 2

    wb.save(output_excel)


def process_sales_zip(sales_folder, output_path, progress_callback=None):
    sales_folder = pathlib.Path(sales_folder)
    pdf_files = find_pdfs(sales_folder)
    if not pdf_files:
        raise ValueError("No PDF files were found in the ZIP.")

    job_id = uuid.uuid4().hex[:8]
    LOGGER.info("Sales job %s queued %d PDF(s)", job_id, len(pdf_files))
    data_rows = asyncio.run(
        _process_sales_files(pdf_files, sales_folder, progress_callback, job_id)
    )

    if not data_rows:
        raise RuntimeError(f"Could not process any of the {len(pdf_files)} PDF files.")

    write_to_excel_with_categories(pd.DataFrame(data_rows), output_path)
    failed = len(pdf_files) - len(data_rows)
    LOGGER.info(
        "Sales job %s complete: %d processed, %d failed",
        job_id, len(data_rows), failed,
    )
    return len(data_rows), failed
