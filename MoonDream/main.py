# main.py (Corrected for server)
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image
import torch
import io
import traceback # Import for better error logging

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

print("Loading Moondream model...")
moon_model_id = "vikhyatk/moondream2"
moon_model = AutoModelForCausalLM.from_pretrained(moon_model_id, trust_remote_code=True).to(device)
moon_tokenizer = AutoTokenizer.from_pretrained(moon_model_id)
print("Moondream model loaded.")

def get_moondream_caption(image: Image.Image) -> str:
    """Gets the caption from the Moondream model."""
    # Moondream2 uses a specific method to answer questions. Let's ask it to describe.
    # The prompt "What is written on the board?" is more direct than just captioning.
    enc_image = moon_model.encode_image(image)
    caption = moon_model.answer_question(enc_image, "Describe the scene.", moon_tokenizer)
    return caption

def extract_commands_from_caption(caption: str) -> list:
    """Finds all known LED commands within the caption text."""
    print(f"[Logic] Analyzing caption for commands: '{caption}'")
    
    # This function now uses simple string searching, no second AI model needed for this task.
    # This is faster, more reliable, and avoids the previous prompt issues.
    found_commands = []
    caption_lower = caption.lower()
    
    # Define our command keywords
    VALID_COMMANDS = ["red led", "yellow led", "green led", "blue led", "all off"]

    # If "all off" is present, it's the only command that matters
    if "all off" in caption_lower:
        print("[Logic] Found command: All Off")
        return ["All Off"]

    # Otherwise, check for each individual LED command
    for command in VALID_COMMANDS:
        if command != "all off" and command in caption_lower:
            # Capitalize for clean output, e.g., "Red LED"
            clean_command = command.replace("led", "LED").title() 
            print(f"[Logic] Found command: {clean_command}")
            found_commands.append(clean_command)

    if not found_commands:
        return ["None"] # Return a list containing "None"
    else:
        return found_commands # Return the list of found commands

@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        print(f"[INFO] Received file: {file.filename}")
        caption = get_moondream_caption(image)
        print(f"[MOONDREAM] Caption: {caption}")

        # Use the reliable string parsing function instead of a second LLM
        extracted_commands = extract_commands_from_caption(caption)
        print(f"[Logic] Extracted Commands: {extracted_commands}")

        return {
            "caption": caption,
            "interpretation": extracted_commands # The key is now 'interpretation' but holds a list of commands
        }

    except Exception as e:
        print(f"[ERROR] An error occurred in analyze_image: {e}")
        traceback.print_exc() # Print full traceback for debugging
        return {"error": str(e)}
