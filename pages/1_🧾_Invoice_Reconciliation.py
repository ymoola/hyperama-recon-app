import streamlit as st
import glob
import json
from utils.auth import check_auth
from utils.extract import extract_statement, extract_invoice_info
from utils.helpers import (
    uploaded_pdf_to_tempfile,
    uploaded_zip_to_tempfile,
    unzip_and_process,
    reconcile_with_statement,
    export_combined_results
)



def process_invoice_folder(zip_file, statement_markdown):
    results = []
    folder_path = unzip_and_process(uploaded_zip_to_tempfile(zip_file))
    for file in glob.glob(folder_path + '/*'):
        for f in glob.glob(file + '/*'):
            if f.endswith(".pdf"):
                info = extract_invoice_info(f)
                reconciled = reconcile_with_statement(info, statement_markdown)
                results.append(json.loads(reconciled))
    return results


st.set_page_config(page_title="Invoice Reconciliation", layout="centered")
st.title("📁 Invoice Reconciliation")

if not check_auth():
    st.stop()

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

cc_pdf = st.file_uploader("Upload Credit Card Statement (PDF)", type="pdf")
bank_pdf = st.file_uploader("Upload Bank Statement (PDF)", type="pdf")
cc_zip = st.file_uploader("Upload Invoices for Credit Card (ZIP)", type="zip")
bank_zip = st.file_uploader("Upload Invoices for Bank (ZIP)", type="zip")

if st.button("🔄 Run Reconciliation") and cc_pdf and cc_zip and bank_zip and bank_pdf:
    with st.spinner("🔍 Extracting statements..."):
        try:
            credit_path = uploaded_pdf_to_tempfile(cc_pdf)
            cc_md = extract_statement(credit_path)
        except Exception as e:
            st.error(f"Error extracting credit card statement: {e}")

        try:
            bank_md_path = uploaded_pdf_to_tempfile(bank_pdf)
            bank_md = extract_statement(bank_md_path)
        except Exception as e:
            st.error(f"Error extracting bank statement: {e}")

    if cc_md:
        with st.spinner("📄 Extracting credit card invoices..."):
            results_cc = process_invoice_folder(cc_zip, cc_md) if cc_md else []
    else:
        st.error("Error extracting credit card statement. Please try again.")

    if bank_md:
        with st.spinner("📄 Extracting bank invoices..."):
            results_bank = process_invoice_folder(bank_zip, bank_md) if bank_md else []
    else:
        st.error("Error extracting bank statement. Please try again.")

    final_path = export_combined_results(results_cc, results_bank)
    with open(final_path, "rb") as f:
        final_bytes = f.read()
        st.session_state["final_recon"] = final_bytes

    st.success("✅ Reconciliation complete!")

if "final_recon" in st.session_state:
    st.download_button("📥 Download Reconciliation Excel", st.session_state["final_recon"], file_name="reconciliation_results.xlsx")
