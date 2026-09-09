from datetime import date, timedelta


statement_extraction_prompt = """
            Analyze the statement in the provided document. Extract all readable content
            and present it in a structured Markdown format that is clear, concise, 
            and well-organized. Use headings, lists, or tables where appropriate. EXTRACT ALL CONTENT."""

invoice_extraction_prompt = """You're a receipt parser. The following images are pages from one receipt. Extract the vendor name, total amount, tax total/hst and date from the receipt image. 
            Return in JSON format.If Total amount is 0.00, extract subtotal and add on any tax and save it under Total. Always format date in MM/DD/YYYY format.
            Do not wrap output in ```json ```  
            
            Here are the vendor categories:
            {}
            
            Please assign the receipt to one of the above categories based on the vendor name and add this to the json return.
            """

reconciliation_prompt = """
- You are an invoice reconciler agent. You will be given a json of an invoice and your job is to reconcile the invoice with the credit card or bank statement.
- If the invoice is found in the statement, append to the input json with the following key value pair: "reconciled": true
- If the invoice is not found in the statement, append to the input json with the following key value pair: "reconciled": false
- Do not wrap output in ```json ```
"""

def build_sales_extraction_prompt(today=None):
    today = today or date.today()
    previous_month = today.replace(day=1) - timedelta(days=1)
    date_context = (
        f"Today's date is {today:%Y-%m-%d}. Sales reports are usually generated "
        f"for the previous month, which is {previous_month:%B %Y}. For example, "
        f"when that is the expected month, 1/{previous_month.month}/{previous_month.year} "
        f"is likely 1 {previous_month:%B %Y} (DD/MM), while "
        f"{previous_month.month}/1/{previous_month.year} is likely "
        f"{previous_month:%B} 1, {previous_month.year} (MM/DD). Both must be "
        f"returned as {previous_month:%Y-%m}-01."
    )
    return """

You are a sales report extractor for a grocery and diner business. Read this sales report PDF and return a JSON object with the exact fields below.

Group each sales field based on its section header in the report. 

For example, DINER Cash Sales and RETAIL Cash Sales are distinct. Similarly Retail - Account Sales - E-Transfer and Diner - Account Sales - E-Transfer are distinct .

Return this structured JSON:

{
  "Date": "YYYY-MM-DD",

  "Retail - ODOO POS Sales": 0,
  "Retail - Credit Card Sales": 0,
  "Retail - Account Sales - E-Transfer": 0,
  "Retail - Cash Sales": 0,
  "Retail - Actual Cash": 0,
  "Retail - Short / Over": 0,
  "Retail - Account Sales - Aslam/Ayesha": 0,
  "Retail - Account Sales - Product Write-Off": 0,
  "Retail - PlanB - Customer Account": 0,

  "Diner - ODOO POS Sales": 0,
  "Diner - Credit Card Sales": 0,
  "Diner - Uber": 0,
  "Diner - Cash Sales": 0,
  "Diner - Actual Cash": 0,
  "Diner - Short / Over": 0,
  "Diner - Tip": 0,

  "Shopify - Sales": 0,
  "Shopify - Refunds": 0,

  "Total Sales": 0,
  "Total Cash Sales": 0,

  "Notes": ""
}

Instructions:
- If a value is missing in the report, return 0 for that field.
- For the "Notes" field, combine all note-like text (e.g. any freeform text next to a number or under AMOUNT NOTES) into a summary string, referencing which field each note belongs to.
- Return the "Date" field in ISO YYYY-MM-DD format.
- {date_context}
- Resolve the actual calendar date before formatting it. Source dates may use
  DD/MM/YYYY or MM/DD/YYYY; do not assume one format from an ambiguous date alone.
- First use explicit evidence such as a written month, report period, headings,
  and unambiguous dates. For example, 13/08 can only be DD/MM, while 08/13 can
  only be MM/DD. Apply the detected convention consistently throughout the PDF.
- For dates where both parts are 12 or less, use that evidence to disambiguate.
  If the document provides no decisive evidence, use the usual previous-month
  reporting period above as the tie-breaker.
- Do not force the previous month when the document clearly identifies another
  reporting month.
- Only return the JSON object with exact matching field names.
""".replace("{date_context}", date_context)
