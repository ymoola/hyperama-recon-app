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

Here is the invoice:
---
{}
---
And here is the credit card or bank statement markdown:
---
{}
---
"""

sales_extraction_prompt = """

You are a sales report extractor for a grocery and diner business. Read this sales report PDF and return a JSON object with the exact fields below.

Group each sales field based on its section header in the report. 

For example, DINER Cash Sales and RETAIL Cash Sales are distinct. Similarly Retail - Account Sales - E-Transfer and Diner - Account Sales - E-Transfer are distinct .

Return this structured JSON:

{
  "Date": "DD-MM-YYYY",

  "Retail - ODOO POS Sales": 0,
  "Retail - Credit Card Sales": 0,
  "Retail - Account Sales - E-Transfer": 0,
  "Retail - Cash Sales": 0,
  "Retail - Actual Cash": 0,
  "Retail - Short / Over": 0,
  "Retail - Account Sales - Aslam/Ayesha": 0,
  "Retail - Account Sales - Product Write-Off": 0,

  "Diner - ODOO POS Sales": 0,
  "Diner - Credit Card Sales": 0,
  "Diner - Account Sales - E-Transfer": 0,
  "Diner - Uber": 0,
  "Diner - Cash Sales": 0,
  "Diner - Actual Cash": 0,
  "Diner - Short / Over": 0,
  "Diner - Staff Meal": 0,
  "Diner - Account Sales - Aslam/Ayesha": 0,
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
- Ensure the "Date" field is in DD-MM-YYYY format.
- Only return the JSON object with exact matching field names.
"""