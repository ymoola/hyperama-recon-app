from google import genai
from openai import OpenAI
from typing import Optional
from pydantic import BaseModel
import streamlit as st


#------ Load environment and Gemini client------
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
genai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

#------ Vendor Categories ------
vendor_categories = {
    "SA Imports": ["Rasheeda Industries", "L&K Poly"],
    "Clearing, FF, Duties, W/housing": ["Shuttle Freight"],
    "Meat": ["St Helens", "Sargent Farms", "Toronto Halal", "Sysco", "Solmaz", "Bacha Casings", "J&FC Seafood"],
    "Local Purchases": ["Sysco", "A1", "Bun Man", "Sahel Khan", "Starsky", "Mr Produce", "Walmart", "PIX Graphics", "Kim Eco Pak"],
    "Utilities": ["Alectra", "Enbridge", "Rogers", "Telus"],
    "Rent": ["SDEB"],
    "Repairs & Maintenance": ["MechArm", "IB Technical", "Just instruments", "Willy Oosthuizen", "Skypole"],
    "Office Expenses": ["Amazon"],
    "Health & Safety": ["Green Planet", "Abell Pest Control", "Cintas", "CFIA", "HMA", "Waste Connection of Canada", "Aqua Team Power Clean"],
    "Insurance, Legal, Accounting": ["Des Jardin", "HHAcc Services"],
    "Bank charges": ["RBC", "Moneris"],
    "Delivery service": ["Uber Eats", "Door Dash"],
    "Freight on line shopping": ["Click ship (Freight.com)"],
    "Vehicle & Fuel": ["Nissan", "Stinton", "Shell"],
    "Consulting": ["Food safety first"]
}

#------ Receipt Schema ------
receipt_schema = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": "string"},
        "total_amount": {"type": "string"},
        "tax_total": {"type": "string"},
        "date": {"type": "string"},
        "category": {"type": "string"}
    },
    "required": ["vendor_name", "total_amount", "tax_total", "date", "category"],
    "additionalProperties": False
}


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