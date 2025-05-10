import streamlit as st
import pathlib
import base64
from openai import OpenAI
from pdf2image import convert_from_path
from google import genai
from google.genai.types import Part
from dotenv import load_dotenv

load_dotenv()
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
genai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

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

def extract_statement(pdf_path):
    filepath = pathlib.Path(pdf_path)
    prompt = """Analyze the statement in the provided document. Extract all readable content
            and present it in a structured Markdown format that is clear, concise, 
            and well-organized. Use headings, lists, or tables where appropriate. EXTRACT ALL CONTENT."""
    response = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            Part.from_bytes(
                data=filepath.read_bytes(),
                mime_type='application/pdf',
            ),
            prompt
        ]
    )
    print(response.text)
    return response.text

def pdf_to_base64_images(pdf_path):
    images = convert_from_path(pdf_path, dpi=200)
    base64_images = []
    for i, image in enumerate(images):
        temp_path = f"temp_page_{i+1}.jpg"
        image.save(temp_path, "JPEG")
        with open(temp_path, "rb") as f:
            base64_images.append(base64.b64encode(f.read()).decode("utf-8"))
    return base64_images

def extract_invoice_info(pdf_path):
    base64_images = pdf_to_base64_images(pdf_path)
    message_content = [{
        "type": "text",
        "text": (
            f"""You're a receipt parser. The following images are pages from one receipt. Extract the vendor name, total amount, tax total/hst and date from the receipt image. 
            Return in JSON format.If Total amount is 0.00, extract subtotal and add on any tax and save it under Total. Always format date in MM/DD/YYYY format.
            Do not wrap output in ```json ```  
            
            Here are the vendor categories:
            {vendor_categories}
            
            Please assign the receipt to one of the above categories based on the vendor name and add this to the json return.
            """
        )
    }]
    for b64_img in base64_images:
        message_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_img}"
            }
        })

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": message_content}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "receipt_info",
                "schema": receipt_schema,
                "strict": True
            }
        },
        max_tokens=500
    )
    return response.choices[0].message.content
