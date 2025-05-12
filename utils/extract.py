import pathlib
import base64
from pdf2image import convert_from_path
from config.settings import (openai_client, genai_client, 
                             vendor_categories, receipt_schema)
from google.genai.types import Part

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
