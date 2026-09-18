import base64, io
from openai import OpenAI   
from openai import AuthenticationError
from PIL import Image
import config
placeholder = 'null'
try:
    placeholder = config.api_key

except Exception:
    placeholder = 'null'

client = OpenAI(
    api_key = placeholder
)

import json
import re

def parse_names_response(text: str) -> list[str]:
    # try direct JSON parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # extract JSON array from markdown/codeblock
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError("No JSON array found in response")

    return json.loads(m.group(0))

def pil_to_data_url(pil_img: Image.Image) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def read_6_names_from_image(stacked_img: Image.Image, model="gpt-4.1-mini"):
    data_url = pil_to_data_url(stacked_img)

    prompt = (
        "This image contains EXACTLY 6 player names, one per line (top to bottom).\n"
        "Return ONLY a JSON array of 6 strings in order.\n"
        "Preserve exact case and Unicode.\n"
        "Usernames are case-sensitive and typically begin with letters, not digits.\n"
        "Preserve dots, underscores, and capitalization.\n"
        "Do not add explanations."
    )
    try:
        resp = client.responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url},
                ],
            }],
            # If you want stricter reliability, use Structured Outputs (below).
        )

        # The SDK exposes the combined text output like this:
        txt = resp.output_text.strip()
        return txt
    except AuthenticationError:
        print("❌ Invalid or missing API key")
        placeholder = "null"
        config.save_api_key(placeholder)

    except Exception as e:
        print("Other OpenAI error:", e)
