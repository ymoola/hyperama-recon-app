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
Extract the daily sales report from this PDF. 
Make sure the "Date" field is in DD-MM-YYYY format.
For "Notes", summarize any note-related cells and include the associated column names (if available). If no notes, set it as an empty string.
"""