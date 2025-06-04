import pathlib
import base64
from pdf2image import convert_from_path
from config.settings import (openai_client, genai_client, 
                             vendor_categories, receipt_schema)
from google.genai.types import Part
from utils.prompts import statement_extraction_prompt, invoice_extraction_prompt

def extract_statement(pdf_path):
    filepath = pathlib.Path(pdf_path)
    prompt = statement_extraction_prompt
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
    prompt = invoice_extraction_prompt.format(vendor_categories)
    message_content = [{
        "type": "text",
        "text": prompt
    }]
    for b64_img in base64_images:
        message_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_img}"
            }
        })

    response = openai_client.chat.completions.create(
        model="o4-mini",
        messages=[{"role": "user", "content": message_content}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "receipt_info",
                "schema": receipt_schema,
                "strict": True
            }
        },
        #max_tokens=500
    )
    return response.choices[0].message.content
