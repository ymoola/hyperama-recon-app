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
    split_and_export,
    export_combined_results
)

if check_auth():
    st.set_page_config(page_title="Invoice Reconciler", layout="centered")
    st.title("📁 Invoice Reconciliation App")

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
                print("cc statement extracted")
            except Exception as e:
                st.error(f"Error extracting credit card statement: {e}")

            try:
                bank_md_path = uploaded_pdf_to_tempfile(bank_pdf)
                bank_md = extract_statement(bank_md_path)
                print("bank statement extracted")
            except Exception as e:
                st.error(f"Error extracting bank statement: {e}")

        cc_folder = unzip_and_process(uploaded_zip_to_tempfile(cc_zip))
        bank_folder = unzip_and_process(uploaded_zip_to_tempfile(bank_zip))

        results_cc, results_bank = [], []

        if cc_md:
            with st.spinner("🤖 Processing Credit Card invoices..."):
                for file in glob.glob(cc_folder + '/*'):
                    for f in glob.glob(file + '/*'):
                        if f.endswith(".pdf"):
                            info = extract_invoice_info(f)
                            reconciled = reconcile_with_statement(info, cc_md)
                            results_cc.append(json.loads(reconciled))

        if bank_md:
            with st.spinner("🤖 Processing Bank invoices..."):
                for file in glob.glob(bank_folder + '/*'):
                    for f in glob.glob(file + '/*'):
                        if f.endswith(".pdf"):
                            info = extract_invoice_info(f)
                            reconciled = reconcile_with_statement(info, bank_md)
                            results_bank.append(json.loads(reconciled))

        final_path = export_combined_results(results_cc, results_bank)
        with open(final_path, "rb") as f:
            final_bytes = f.read()
            st.session_state["final_recon"] = final_bytes

        st.success("✅ Reconciliation complete!")

    if "final_recon" in st.session_state:
        st.download_button("📥 Download Reconciliation Excel", st.session_state["final_recon"], file_name="reconciliation_results.xlsx")

