import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd
from config.settings import get_openai_client, receipt_schema
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font
from utils.prompts import reconciliation_prompt


MAX_ZIP_FILES = 1_000
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024


def save_upload(uploaded_file, directory, filename):
    path = Path(directory) / filename
    path.write_bytes(uploaded_file.getvalue())
    return path


def extract_zip(zip_path, destination, max_files=MAX_ZIP_FILES,
                max_bytes=MAX_UNCOMPRESSED_BYTES):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) > max_files:
            raise ValueError(f"ZIP contains more than {max_files:,} files.")
        if sum(member.file_size for member in members) > max_bytes:
            raise ValueError("ZIP expands beyond the 500 MB safety limit.")

        for member in members:
            path = PurePosixPath(member.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("ZIP contains an unsafe file path.")
            if stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError("ZIP contains an unsupported symbolic link.")

        archive.extractall(destination)
    return destination


def find_pdfs(directory):
    directory = Path(directory)
    return sorted(
        path for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
        and "__MACOSX" not in path.relative_to(directory).parts
        and not any(part.startswith(".") for part in path.relative_to(directory).parts)
    )


def reconcile_with_statement(invoice_json, statement_md):
    schema = {
        **receipt_schema,
        "properties": {
            **receipt_schema["properties"],
            "reconciled": {"type": "boolean"},
        },
        "required": [*receipt_schema["required"], "reconciled"],
    }
    response = get_openai_client().chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "developer", "content": reconciliation_prompt},
            {
                "role": "user",
                "content": f"Invoice JSON:\n{invoice_json}\n\nStatement:\n{statement_md}",
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "reconciliation_result",
                "schema": schema,
                "strict": True,
            },
        },
    )
    return json.loads(response.choices[0].message.content)


def export_combined_results(results_cc, results_bank, output_path):
    matched, unmatched = [], []

    for source, results in (("credit card", results_cc), ("bank", results_bank)):
        for result in results:
            entry = {**result, "source": source}
            (matched if entry.get("reconciled") is True else unmatched).append(entry)

    if not matched and not unmatched:
        raise ValueError("No invoices were successfully processed.")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, entries in (("Matched", matched), ("Unmatched", unmatched)):
            if not entries:
                continue
            dataframe = pd.DataFrame(entries)
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            for col_num in range(1, len(dataframe.columns) + 1):
                worksheet[f"{get_column_letter(col_num)}1"].font = Font(bold=True)

    return Path(output_path)
