import base64
import logging
import pathlib
import time
from io import BytesIO

from pdf2image import convert_from_path
from google.genai.types import Part

from config.settings import (
    create_genai_client,
    get_openai_client,
    receipt_schema,
    vendor_categories,
)
from utils.gemini_limits import (
    MAX_ATTEMPTS,
    get_gemini_coordinator,
    is_retryable,
    response_tokens,
    retry_delay,
)
from utils.prompts import statement_extraction_prompt, invoice_extraction_prompt


LOGGER = logging.getLogger(__name__)


def extract_statement(pdf_path):
    filepath = pathlib.Path(pdf_path)
    contents = [
        Part.from_bytes(data=filepath.read_bytes(), mime_type="application/pdf"),
        statement_extraction_prompt,
    ]
    coordinator = get_gemini_coordinator()

    with create_genai_client() as client:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            reservation = coordinator.wait_for_reservation()
            actual_tokens = None
            wait = None
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash", contents=contents
                )
                actual_tokens = response_tokens(response)
                return response.text
            except Exception as error:
                if attempt == MAX_ATTEMPTS or not is_retryable(error):
                    raise
                wait = retry_delay(error, attempt)
                LOGGER.warning(
                    "Retrying statement %s in %.1fs after %s",
                    filepath.name, wait, error,
                )
            finally:
                coordinator.release(reservation, actual_tokens)
            time.sleep(wait)


def pdf_to_base64_images(pdf_path):
    images = convert_from_path(pdf_path, dpi=200)
    base64_images = []
    for image in images:
        buffer = BytesIO()
        image.save(buffer, "JPEG")
        base64_images.append(base64.b64encode(buffer.getvalue()).decode("utf-8"))
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

    response = get_openai_client().chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": message_content}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "receipt_info",
                "schema": receipt_schema,
                "strict": True
            }
        }
    )
    return response.choices[0].message.content
