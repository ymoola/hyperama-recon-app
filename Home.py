import streamlit as st

st.set_page_config(page_title="Welcome", layout="centered")

st.title("🇿🇦 Hyperama Financial Assistant")
st.markdown(
    """
Welcome to the **Hyperama Financial Assistant**.

This tool offers two services to support your financial operations:

---

### 🧾 Invoice Reconciliation
Match your **invoices** against **credit card or bank statements** and generate a fully reconciled Excel report.

✅ Automatically categorize vendors  
✅ Highlight unreconciled invoices  
✅ Download results in a structured workbook

---

### 📈 Sales Report Generation
Convert **daily sales report PDFs** into a **well-structured Excel summary** with categorized columns and clean formatting.

✅ Group fields under custom categories  
✅ Auto-format headers and columns  
✅ Export one-click Excel summaries

---

To get started, choose a service from the **sidebar on the left**.

🔒 *Authentication is required to access service pages.*
"""
)
