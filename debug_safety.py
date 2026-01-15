import os
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pathlib import Path

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_prompt(name, prompt_text, image_paths=None):
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    upload_cache = {}
    
    contents = [prompt_text]
    if image_paths:
        for p in image_paths:
            path = Path(p)
            if not path.exists():
                logger.error(f"Missing file: {p}")
                continue
            logger.info(f"Uploading {p}...")
            f = client.files.upload(file=str(path))
            contents.append(f)

    logger.info(f"--- TESTING PROMPT: {name} ---")
    logger.info(f"Prompt length: {len(prompt_text)}")
    
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="4:5", image_size="2K"),
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ],
    )

    try:
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=config,
        )
        
        if response.candidates:
            logger.info("SUCCESS: Candidates returned.")
            # print first candidate
            print(response.candidates[0])
        else:
            logger.warning("FAILURE: No candidates.")
            print(response.prompt_feedback)
            
    except Exception as e:
        logger.error(f"EXCEPTION: {e}")

# 1. Full Provocative Prompt (from Log)
full_prompt = """
Photorealistic raw photo, Finnish Reservist aesthetic, Ranger Green or Grey gear, grainy, high ISO, crushed blacks, desaturated greens/blues. Shot on 35mm film, harsh on-camera flash. Documentary style, not cinematic. Hoodie must exactly match the provided reference images. Gear must be solid Ranger Green or Grey. NO Camo patterns on gear. Trust the reference images for all gear branding and details. No unapproved text or logos; if gear has visible brands in references, they are allowed. Back view of Finnish reservist wearing the reference hoodie standing still, shoulders relaxed, rifle low, face fully obscured by hood and angle, harsh flash, Ranger Green gear visible, back design matches reference and may be partially occluded by gear
"""

# 2. Sanitized Prompt (No "rifle", "reservist", "flash", "warcore" vibes explicitly minimized)
sanitized_prompt = """
Photorealistic raw photo, outdoor adventurer aesthetic, Ranger Green or Grey gear, grainy, high ISO, crushed blacks, desaturated greens/blues. Shot on 35mm film. Documentary style. Hoodie must exactly match the provided reference images. Gear must be solid Ranger Green or Grey. Trust the reference images for all gear branding and details. Back view of person wearing the reference hoodie standing still, shoulders relaxed, holding gear low, face fully obscured by hood and angle.
"""

if __name__ == "__main__":
    # Test 1: Full Prompt Text Only
    test_prompt("Full Text Only", full_prompt, [])
    
    # Test 2: Sanitized Text Only
    test_prompt("Sanitized Text Only", sanitized_prompt, [])
    
    # Test 3: Full Text + Hoodie Ref (No Weapon)
    params_path = "assets/references/hoodies/hoodie_rk_black_back.webp"
    test_prompt("Full Text + Ref", full_prompt, [params_path])

    # Test 4: Sanitized Text + Ref
    test_prompt("Sanitized Text + Ref", sanitized_prompt, [params_path])

    # Test 5: Full Text + Env Image
    env_path = "assets/references/ENV_TAIGA_WINTER_KAAMOS/taiga_winter_kaamos_01.jpg"
    test_prompt("Full Text + Env Image", full_prompt, [env_path])
