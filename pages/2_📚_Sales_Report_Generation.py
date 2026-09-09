import streamlit as st
from pathlib import Path
from tempfile import TemporaryDirectory

from utils.auth import check_auth
from utils.helpers import extract_zip, save_upload
from utils.sales_helpers import process_sales_zip

st.set_page_config(page_title="Sales Report Generator", layout="centered")
st.title("📊 Sales Report Generator")

if not check_auth():
    st.stop()

if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

sales_zip = st.file_uploader("Upload ZIP of Sales PDFs", type="zip")

if st.button("🛠 Generate Sales Report"):
    if not sales_zip:
        st.warning("Upload a ZIP of sales PDFs first.")
    else:
        st.session_state.pop("sales_report_bytes", None)
        progress = st.progress(0, text="Preparing sales PDFs...")
        try:
            with st.spinner("📦 Extracting and processing PDFs..."):
                with TemporaryDirectory() as workspace:
                    workspace = Path(workspace)
                    archive = save_upload(sales_zip, workspace, "sales.zip")
                    sales_folder = extract_zip(archive, workspace / "sales")
                    output_path = workspace / "monthly_sales_report.xlsx"
                    processed, failed = process_sales_zip(
                        sales_folder,
                        output_path,
                        lambda current, total, name, status: progress.progress(
                            current / total,
                            text=f"Completed {current} of {total}: {name} ({status})",
                        ),
                    )
                    st.session_state["sales_report_bytes"] = output_path.read_bytes()
        except Exception as error:
            progress.empty()
            st.error(f"Sales report generation failed: {error}")
        else:
            progress.progress(100, text=f"Completed {processed} sales PDF(s).")
            if failed:
                st.warning(f"Processed {processed} PDF(s); skipped {failed}.")
            st.success("✅ Sales report ready!")

if "sales_report_bytes" in st.session_state:
    st.download_button(
        "📥 Download Sales Report",
        st.session_state["sales_report_bytes"],
        file_name="monthly_sales_report.xlsx",
    )
