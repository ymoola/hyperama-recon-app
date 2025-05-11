import os
import tempfile
import zipfile
import json
import pandas as pd
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font
from openpyxl import load_workbook
from openai import OpenAI
import streamlit as st

openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def uploaded_pdf_to_tempfile(uploaded_file):
    suffix = ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.read())
        return temp_file.name

def uploaded_zip_to_tempfile(uploaded_file):
    suffix = ".zip"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.read())
        return temp_file.name

def unzip_and_process(zip_file):
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_file, "r") as zip_ref:
        zip_ref.extractall(temp_dir)
    return temp_dir

def reconcile_with_statement(invoice_json, statement_md):
    prompt = f"""
- You are an invoice reconciler agent. You will be given a json of an invoice and your job is to reconcile the invoice with the credit card or bank statement.
- If the invoice is found in the statement, append to the input json with the following key value pair: "reconciled": true
- If the invoice is not found in the statement, append to the input json with the following key value pair: "reconciled": false
- Do not wrap output in ```json ```

Here is the invoice:
---
{invoice_json}
---
And here is the credit card or bank statement markdown:
---
{statement_md}
---
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    return response.choices[0].message.content


def export_combined_results(results_cc, results_bank, output_path="reconciliation_results.xlsx"):
    matched, unmatched = [], []

    for entry in results_cc:
        entry["source"] = "credit card"
        if entry.get("reconciled") is True:
            matched.append(entry)
        else:
            unmatched.append(entry)

    for entry in results_bank:
        entry["source"] = "bank"
        if entry.get("reconciled") is True:
            matched.append(entry)
        else:
            unmatched.append(entry)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        if matched:
            matched_df = pd.DataFrame(matched)
            matched_df.to_excel(writer, sheet_name="Matched", index=False)
            ws = writer.sheets["Matched"]
            for col_num, column_title in enumerate(matched_df.columns, 1):
                ws[f"{get_column_letter(col_num)}1"].font = Font(bold=True)

        if unmatched:
            unmatched_df = pd.DataFrame(unmatched)
            unmatched_df.to_excel(writer, sheet_name="Unmatched", index=False)
            ws = writer.sheets["Unmatched"]
            for col_num, column_title in enumerate(unmatched_df.columns, 1):
                ws[f"{get_column_letter(col_num)}1"].font = Font(bold=True)

    return output_path

