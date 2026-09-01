import base64
import io
import json
import os
import time
from pathlib import Path

from openai import OpenAI, AuthenticationError
from PIL import Image

import config
import helpers


SPECIFIC_HEROES = True
SPECIFIC_HEROES = ["selecthero"]

img_dir = helpers.create_path(folder="lord")
img_save_dir = helpers.create_path(folder="lord chatgpt")

os.makedirs(img_save_dir, exist_ok=True)

LOG_PATH = os.path.join(img_save_dir, "generation_log.json")


try:
    api_key = str(config.api_key).strip()
except Exception:
    api_key = ""

if not api_key or api_key == "null":
    raise RuntimeError("No OpenAI API key is configured.")

if not api_key.startswith("sk-"):
    raise RuntimeError("The configured API key has an invalid format.")

client = OpenAI(api_key=api_key)


PROMPT = (
    "Add to this image more of this characters body. Reveal up to 70% of the characters full body art, as if it was posed exactly as they are in the source image. Do not modify the existing pose, image, or pixels in any way (besides upscaling and adding detail),  INCLUDING transparent pixels (alpha channel). Output result must have transparent pixels. As far as image style, the output should match the following art description: Create a full-body hero character rendered as premium 2D game splash art. Use a crisp inked silhouette, angular shape design, clean contour hierarchy, sculpted planar anatomy, and precise facial rendering. Render shadows as intentional graphic shapes rather than blended paint. Use smooth controlled gradients only inside clearly defined forms. Armor must have sharp beveled edges, distinct overlapping plates, precise decorative motifs, and bright metallic edge highlights. Skin should be smoothly rendered with firm shadow boundaries and subtle warm reflected light. Magical effects should have sharp cyan-white cores, clean translucent outer shapes, and small controlled particles. Every material must remain visually distinct and sharply readable. No visible brush texture"
)
PROMPT = (
    "Extend the supplied character artwork downward and outward, revealing "
    "approximately 70% of the character's full body. Continue the exact implied "
    "pose, anatomy, costume design, lighting direction, and proportions from the "
    "existing artwork. Generate content only within the currently transparent "
    "canvas area. Preserve every existing nontransparent source pixel exactly. "
    "Existing transparent pixels may become opaque only where the newly revealed "
    "character body or effects are added. Keep all remaining background pixels "
    "fully transparent.\n\n"

    "RENDERING PRIORITY: The newly generated portion must use a clean, polished, "
    "texture-free 2D character-rendering finish. Use smooth solid color regions, "
    "precisely bounded shadow shapes, clean tonal gradients, sharp geometric "
    "highlights, and uniformly controlled edges. Surfaces must appear digitally "
    "airbrushed and graphic, not painted. Use hard or deliberately controlled "
    "shadow boundaries. Keep skin, fabric, metal, hair, and energy separated into "
    "clear, uninterrupted material regions. Armor edges must be sharply constructed "
    "with clean bevel highlights and precise overlapping plates.\n\n"

    "Do not create visible brush marks, dry-brush texture, canvas texture, watercolor "
    "variation, oil-paint strokes, sketch marks, hatched shading, rough color breakup, "
    "impasto, smeared transitions, irregular painted edges, or decorative texture "
    "inside otherwise smooth surfaces. Do not imitate the source image's brush texture "
    "in the newly generated area. Match its character identity, design, pose, palette, "
    "and lighting, but render the extension with a cleaner and smoother production finish."
)
PROMPT = (
    "Extend the supplied character artwork downward and outward, revealing "
    "approximately 70% of the character's full body. Continue the exact implied "
    "pose, anatomy, costume design, lighting direction, proportions, and perspective "
    "from the existing artwork. Generate new content only within the currently "
    "transparent canvas area. Preserve every existing nontransparent source pixel "
    "exactly. Existing transparent pixels may become opaque only where the newly "
    "revealed character body, costume, hair, weapon, or effects are added. Keep all "
    "remaining background pixels fully transparent.\n\n"

    "RENDERING PRIORITY: Render the newly generated body as sophisticated, polished "
    "semi-realistic 2D game character artwork. Maintain clean contours and highly "
    "controlled surfaces, but avoid flat cartoon rendering or simple cel shading. "
    "Use naturally sculpted anatomy, believable body volume, nuanced facial and "
    "muscular structure, realistic costume construction, and detailed layered materials. "
    "Forms should be modeled through several controlled values of light, midtone, "
    "core shadow, reflected light, and occlusion shadow rather than one flat highlight "
    "and one flat shadow shape.\n\n"

    "Use refined digital rendering with smooth tonal transitions where appropriate, "
    "firm but natural shadow boundaries, subtle surface variation, and carefully placed "
    "high-frequency detail. Preserve crisp edges around the silhouette, armor plates, "
    "costume seams, facial features, fingers, hair groups, and weapon geometry. Use "
    "selective soft edges only across rounded skin, fabric folds, atmospheric glow, "
    "and curved materials. Avoid uniformly hard edges across every surface.\n\n"

    "Armor and hard-surface elements must have precise construction, layered plates, "
    "realistic thickness, beveled edges, small mechanical details, controlled metallic "
    "reflections, and material-specific highlights. Fabric should show subtle folds, "
    "tension, compression, seams, and restrained texture. Skin should have believable "
    "anatomical planes, subtle color variation, warm and cool transitions, and smooth "
    "professional rendering without looking plastic. Hair should be organized into "
    "defined flowing masses with selective fine strands, not simple solid shapes.\n\n"

    "The final result should resemble premium modern action-game character key art: "
    "mature, detailed, dimensional, anatomically convincing, and production-polished. "
    "Use slightly stylized proportions, but retain realistic structure and complexity. "
    "Maintain strong contrast and readable shapes without reducing the design into "
    "large flat graphic color blocks.\n\n"

    "Do not use visible brush strokes, watercolor texture, dry-brush marks, canvas grain, "
    "rough concept-art texture, muddy blending, sketch lines, or smeared edges. Also avoid "
    "flat cel shading, comic-book coloring, vector-art simplicity, low-detail surfaces, "
    "oversized geometric anatomy, toy-like proportions, plastic materials, thick uniform "
    "outlines, posterized shading, broad empty color regions, or simplified animated-TV styling.\n\n"

    "Match the source character's identity, costume, pose, palette, lighting, and design. "
    "Do not inherit obvious brush texture from the source, but retain its visual complexity, "
    "maturity, dimensionality, and level of anatomical detail."
)
def make_png_list(directory: str) -> list[str]:
    """Return alphabetically sorted PNG filenames in a directory."""
    return sorted(
        filename
        for filename in os.listdir(directory)
        if filename.lower().endswith(".png")
        and os.path.isfile(os.path.join(directory, filename))
    )


def load_log() -> dict:
    """Load the persistent generation log."""
    if not os.path.exists(LOG_PATH):
        return {}

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except (OSError, json.JSONDecodeError):
        pass

    return {}


def save_log(log: dict) -> None:
    """
    Save the log atomically so an interrupted write does not destroy it.
    """
    temporary_path = LOG_PATH + ".tmp"

    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(log, file, indent=4, ensure_ascii=False)

    os.replace(temporary_path, LOG_PATH)


def image_to_png_buffer(image: Image.Image) -> io.BytesIO:
    """
    Convert a PIL image into an in-memory RGBA PNG accepted by the API.
    """
    rgba_image = image.convert("RGBA")

    buffer = io.BytesIO()
    rgba_image.save(buffer, format="PNG")
    buffer.seek(0)

    # Some SDK/upload implementations inspect this attribute.
    buffer.name = "input.png"

    return buffer


def image_request(
    source_image: Image.Image,
    model: str = "gpt-image-1",
) -> tuple[bytes, dict]:
    """
    Submit one image-edit request.

    Returns:
        Tuple containing:
        - generated PNG bytes
        - metadata dictionary
    """
    image_buffer = image_to_png_buffer(source_image)
    
    result = client.images.edit(
        
        model="gpt-image-1",
        image=image_buffer,
        prompt=PROMPT,

        # Portrait output gives the model room to add the lower body.
        size="1024x1536",

        quality="high",
        background="transparent",
        output_format="png",

        # Helps retain details from the supplied image.
        input_fidelity="high",
    )

    if not result.data:
        raise RuntimeError("The API returned no image data.")

    image_result = result.data[0]
    encoded_image = image_result.b64_json

    if not encoded_image:
        raise RuntimeError("The API response contained no Base64 image.")

    output_bytes = base64.b64decode(encoded_image)

    metadata = {
        "model": model,
        "size": "1024x1536",
        "quality": "high",
        "background": "transparent",
        "output_format": "png",
    }

    return output_bytes, metadata


def start_prompting_from_list(
    filenames: list[str],
    retries: int = 0,
    retry_delay: float = 5.0,
    overwrite: bool = False,
) -> dict:
    """
    Generate an edited image for every PNG in filenames.

    Successful files are saved in img_save_dir. Progress is continuously
    written to generation_log.json so processing can resume after interruption.
    """
    log = load_log()
    total = len(filenames)

    for index, filename in enumerate(filenames, start=1):
        if "1011" in filename:
        	print("skippping 1011")
        	continue
        	
        if SPECIFIC_HEROES:
            bFound = False
            for hero in SPECIFIC_HEROES:
                #print(hero)
                #print(filename)
                if hero not in filename:            
                    continue
                else:
                    bFound = True
            if not bFound:
                 print(f"Skipping {filename}")
                 continue
            print(f"Found Match: {hero} in {filename}")
            
        
        source_path = os.path.join(img_dir, filename)

        stem, _ = os.path.splitext(filename)
        output_filename = f"{stem}_fullbody5StylePrompt2.png"
        output_path = os.path.join(img_save_dir, output_filename)
        if os.path.exists(output_path):
            print("new skip")
            continue
        previous_entry = log.get(filename, {})

        already_finished = (
            previous_entry.get("status") == "success"
            and os.path.exists(output_path)
        )

        if already_finished and not overwrite:
            print(f"[{index}/{total}] Skipping completed file: {filename}")
            continue

        print(f"\n[{index}/{total}] Processing: {filename}")

        log[filename] = {
            "status": "processing",
            "source_path": source_path,
            "output_path": output_path,
            "attempts": 0,
        }
        save_log(log)

        try:
            with Image.open(source_path) as opened_image:
                source_image = opened_image.convert("RGBA")

                source_metadata = {
                    "width": source_image.width,
                    "height": source_image.height,
                    "mode": source_image.mode,
                }

                for attempt in range(1, retries + 1):
                    log[filename]["attempts"] = attempt
                    save_log(log)

                    try:
                        print(
                            f"    Request attempt {attempt}/{retries}..."
                        )

                        output_bytes, api_metadata = image_request(
                            source_image=source_image
                        )

                        # Verify the returned data is actually a valid image.
                        with Image.open(io.BytesIO(output_bytes)) as result_image:
                            result_image.load()

                            output_metadata = {
                                "width": result_image.width,
                                "height": result_image.height,
                                "mode": result_image.mode,
                                "has_alpha": "A" in result_image.getbands(),
                            }

                        with open(output_path, "wb") as output_file:
                            output_file.write(output_bytes)

                        log[filename] = {
                            "status": "success",
                            "source_path": source_path,
                            "output_path": output_path,
                            "attempts": attempt,
                            "source": source_metadata,
                            "output": output_metadata,
                            "request": api_metadata,
                        }
                        save_log(log)

                        print(f"    Saved: {output_path}")
                        break

                    except AuthenticationError:
                        log[filename] = {
                            "status": "authentication_error",
                            "source_path": source_path,
                            "output_path": output_path,
                            "attempts": attempt,
                            "error": "Invalid or missing API key.",
                        }
                        save_log(log)

                        print("❌ Invalid or missing API key")
                        config.save_api_key("null")

                        # Authentication errors will not improve by retrying.
                        return log

                    except Exception as error:
                        print(f"    Attempt failed: {error}")

                        log[filename]["status"] = "retrying"
                        log[filename]["error"] = repr(error)
                        save_log(log)

                        if attempt >= retries:
                            raise

                        time.sleep(retry_delay)

        except Exception as error:
            log[filename] = {
                "status": "failed",
                "source_path": source_path,
                "output_path": output_path,
                "attempts": log.get(filename, {}).get("attempts", retries),
                "error": repr(error),
            }
            save_log(log)

            print(f"❌ Failed {filename}: {error}")

    return log


if __name__ == "__main__":
    pngs = make_png_list(img_dir)

    print(f"Found {len(pngs)} PNG files in:")
    print(img_dir)

    final_log = start_prompting_from_list(
        filenames=pngs,
        retries=1,
        retry_delay=5,
        overwrite=False,
    )

    succeeded = sum(
        entry.get("status") == "success"
        for entry in final_log.values()
    )

    failed = sum(
        entry.get("status") == "failed"
        for entry in final_log.values()
    )

    print("\nFinished")
    print(f"Successful: {succeeded}")
    print(f"Failed:     {failed}")
    print(f"Log:        {LOG_PATH}")

#import base64, io
#from openai import OpenAI   
#from openai import AuthenticationError
#from PIL import Image
#import config
#import helpers

#img_dir = helpers.create_path(folder="lord")
#img_save_dir = helpers.create_path(folder="lord chatgpt")


#placeholder = 'null'
#try:
#    placeholder = config.api_key

#except Exception:
#    placeholder = 'null'

#client = OpenAI(
#    api_key = placeholder
#)

#import json
#import re
#import os

#def parse_names_response(text: str) -> list[str]:
#    # try direct JSON parse first
#    try:
#        return json.loads(text)
#    except Exception:
#        pass

#    # extract JSON array from markdown/codeblock
#    m = re.search(r"\[.*\]", text, re.DOTALL)
#    if not m:
#        raise ValueError("No JSON array found in response")

#    return json.loads(m.group(0))

#def pil_to_data_url(pil_img: Image.Image) -> str:
#    buf = io.BytesIO()
#    pil_img.save(buf, format="PNG")
#    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
#    return f"data:image/png;base64,{b64}"

#def image_request(stacked_img: Image.Image, model="gpt-4.1-mini"):
#    data_url = pil_to_data_url(stacked_img)

#    prompt = (
#        "Add to this image the rest of this characters body.\n"  
#        "Do not modify the existing pixels in any way, including transparent pixels (alpha channel).\n"
#        "Output result must have transparent pixels."
#    )
#    try:
#        resp = client.responses.create(
#            model=model,
#            input=[{
#                "role": "user",
#                "content": [
#                    {"type": "input_text", "text": prompt},
#                    {"type": "input_image", "image_url": data_url},
#                ],
#            }],
#            # If you want stricter reliability, use Structured Outputs (below).
#        )

#        # The SDK exposes the combined text output like this:
#        txt = resp.output_text.strip()
#        return txt
#    except AuthenticationError:
#        print("❌ Invalid or missing API key")
#        placeholder = "null"
#        config.save_api_key(placeholder)

#    except Exception as e:
#        print("Other OpenAI error:", e)
#        
#def make_png_list(dr):
#        png_names = [
#    filename
#    for filename in os.listdir(dr)
#    if filename.lower().endswith(".png")
#]
#        return png_names
#        
#def start_prompting_from_list(p):
#        log = {}
#        for f in p:
#        	log[f] = {}
#        	path = helpers.create_path(file=f, folder=img_dir)
#        	img = Image.open(path)
#        	response = image_request(stacked_img=img)
#        	
#        	
#        	
#        	
#        
#if __name__ == "__main__":
#	pngs = make_png_list(img_dir)
#	start_prompting_from_list(pngs)
#	
#	
