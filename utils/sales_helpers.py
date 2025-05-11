import pathlib
import glob
import pandas as pd
import streamlit as st
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from google import genai
from google.genai.types import Part


# Load environment and Gemini client
load_dotenv()
client = genai.Client(api_key= st.secrets["GEMINI_API_KEY"])

# === Column Definitions ===
COLUMN_GROUPS = {
    "RETAIL SUPERMARKET & BUTCHERY": [
        "ODOO POS Sales", "Credit Card Sales", "Account Sales - E-Transfer",
        "Cash Sales", "Actual Cash", "Short / Over",
        "Account Sales - Aslam/Ayesha", "Account Sales - Product Write-Off"
    ],
    "DINER": [
        "DINER ODOO POS Sales", "DINER Credit Card Sales", "DINER Account Sales - E-Transfer",
        "Uber", "DINER Cash Sales", "DINER Actual Cash", "DINER Short / Over",
        "Staff Meal", "DINER Account Sales - Aslam/Ayesha", "Tip"
    ],
    "SHOPIFY": ["Shopify Sales", "Shopify Refunds"],
    "SALES SUMMARY": ["Total Sales", "Total Cash Sales"]
}

# === Pydantic Schema ===
class SalesReport(BaseModel):
    Date: str
    ODOO_POS_Sales: float
    Credit_Card_Sales: float
    Account_Sales_E_Transfer: float
    Cash_Sales: float
    Actual_Cash: float
    Short_Over: float
    Account_Sales_Aslam_Ayesha: float
    Account_Sales_Product_Write_Off: float
    Shopify_Sales: float
    Shopify_Refunds: float
    DINER_ODOO_POS_Sales: float
    DINER_Credit_Card_Sales: float
    DINER_Account_Sales_E_Transfer: float
    Uber: float
    DINER_Cash_Sales: float
    DINER_Actual_Cash: float
    DINER_Short_Over: float
    Staff_Meal: float
    DINER_Account_Sales_Aslam_Ayesha: float
    Tip: float
    Total_Sales: float
    Total_Cash_Sales: float
    Notes: Optional[str]

PROMPT = """
Extract the daily sales report from this PDF. 
Make sure the "Date" field is in DD-MM-YYYY format.
For "Notes", summarize any note-related cells and include the associated column names (if available). If no notes, set it as an empty string.
"""

def extract_sales_data(pdf_path: str) -> dict:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            Part.from_bytes(data=pathlib.Path(pdf_path).read_bytes(), mime_type='application/pdf'),
            PROMPT
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": SalesReport
        }
    )
    return response.parsed.model_dump()

def write_to_excel_with_categories(df: pd.DataFrame, output_excel: str):
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")
    df.sort_values("Date", inplace=True)
    df["Date"] = df["Date"].dt.strftime("%d-%m-%Y")

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


def process_sales_zip(sales_folder: str) -> str:
    data_rows = []
    for file in glob.glob(sales_folder + '/*'):
        for f in glob.glob(file + '/*'):
            if f.lower().endswith(".pdf"):
                print(f"📄 Processing: {f}")
                try:
                    row = extract_sales_data(f)
                    data_rows.append(row)
                except Exception as e:
                    print(f"❌ Failed to process {f}: {e}")

    output_path = "monthly_sales_report.xlsx"
    if data_rows:
        df = pd.DataFrame(data_rows)
        write_to_excel_with_categories(df, output_path)
    return output_path
