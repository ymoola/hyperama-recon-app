import streamlit as st
from pathlib import Path
from tempfile import TemporaryDirectory

from utils.auth import check_auth
from utils.extract import extract_statement, extract_invoice_info
from utils.helpers import (
    export_combined_results,
    extract_zip,
    find_pdfs,
    reconcile_with_statement,
    save_upload,
)


def process_invoice_folder(folder_path, statement_markdown):
    pdf_files = find_pdfs(folder_path)
    if not pdf_files:
        raise ValueError("No invoice PDFs were found in one of the ZIP files.")

    results = []
    failures = 0
    for pdf_path in pdf_files:
        try:
            invoice = extract_invoice_info(str(pdf_path))
            results.append(reconcile_with_statement(invoice, statement_markdown))
        except Exception:
            failures += 1

    if not results:
        raise RuntimeError(f"Could not process any of the {len(pdf_files)} invoice PDFs.")
    return results, failures


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

if st.button("🔄 Run Reconciliation"):
    if not all((cc_pdf, bank_pdf, cc_zip, bank_zip)):
        st.warning("Upload both statements and both invoice ZIP files first.")
    else:
        st.session_state.pop("final_recon", None)
        try:
            with TemporaryDirectory() as workspace:
                workspace = Path(workspace)
                credit_path = save_upload(cc_pdf, workspace, "credit-card.pdf")
                bank_path = save_upload(bank_pdf, workspace, "bank.pdf")
                cc_archive = save_upload(cc_zip, workspace, "credit-card.zip")
                bank_archive = save_upload(bank_zip, workspace, "bank.zip")

                with st.spinner("🔍 Extracting statements..."):
                    cc_md = extract_statement(credit_path)
                    bank_md = extract_statement(bank_path)

                cc_folder = extract_zip(cc_archive, workspace / "credit-card-invoices")
                bank_folder = extract_zip(bank_archive, workspace / "bank-invoices")
                with st.spinner("📄 Extracting and reconciling invoices..."):
                    results_cc, failed_cc = process_invoice_folder(cc_folder, cc_md)
                    results_bank, failed_bank = process_invoice_folder(bank_folder, bank_md)

                output_path = export_combined_results(
                    results_cc,
                    results_bank,
                    workspace / "reconciliation_results.xlsx",
                )
                st.session_state["final_recon"] = output_path.read_bytes()
        except Exception as error:
            st.error(f"Reconciliation failed: {error}")
        else:
            failed = failed_cc + failed_bank
            if failed:
                st.warning(f"Skipped {failed} invoice PDF(s) that could not be processed.")
            st.success("✅ Reconciliation complete!")

if "final_recon" in st.session_state:
    st.download_button(
        "📥 Download Reconciliation Excel",
        st.session_state["final_recon"],
        file_name="reconciliation_results.xlsx",
    )
