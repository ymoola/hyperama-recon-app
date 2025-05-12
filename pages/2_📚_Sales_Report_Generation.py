import streamlit as st
import pandas as pd
from utils.auth import check_auth
from utils.helpers import unzip_and_process, uploaded_zip_to_tempfile
from utils.sales_helpers import process_sales_zip

st.set_page_config(page_title="Sales Report Generator", layout="centered")
st.title("📊 Sales Report Generator")

if not check_auth():
    st.stop()

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

sales_zip = st.file_uploader("Upload ZIP of Sales PDFs", type="zip")

if st.button("🛠 Generate Sales Report") and sales_zip:
    with st.spinner("📦 Extracting and Processing PDFs..."):
        sales_folder = unzip_and_process(uploaded_zip_to_tempfile(sales_zip))
        output_path = process_sales_zip(sales_folder)  

        # Save to session state for persistent download
        with open(output_path, "rb") as f:
            st.session_state["sales_report_bytes"] = f.read()

    st.success("✅ Sales Report Ready!")

if "sales_report_bytes" in st.session_state:
    st.download_button("📥 Download Sales Report", st.session_state["sales_report_bytes"], file_name="monthly_sales_report.xlsx")
