# dingavision_client_live.py
# Runs in a continuous loop to provide a "live" response every 30 seconds.

import os
import subprocess
import time
import sys
import requests
from periphery import GPIO

# --- Configuration ---
# IP address of the machine running your DingaVision FastAPI server
DINGA_VISION_IP = "192.168.50.4"
DINGA_VISION_PORT = 8000
DINGA_VISION_URL = f"http://{DINGA_VISION_IP}:{DINGA_VISION_PORT}/analyze-image"

# Path to the USB camera device on the LuckFox
CAMERA_DEVICE = "/dev/video0"

# Temporary file to store the captured image
IMAGE_FILE_PATH = "/tmp/webcam_capture.jpg"

# Map keywords (lowercase) to the GPIO pin number on the LuckFox
# ** IMPORTANT: Change these GPIO numbers to match your actual wiring! **
LED_MAPPING = {
    "red led":    53,
    "yellow led": 52,
    "green led":  54,
    "blue led":   55,
}
# A command to turn all LEDs off
TURN_OFF_KEYWORD = "all off"


def setup_gpios():
    """Initialize GPIO pins as outputs and return a dictionary of GPIO objects."""
    gpio_objects = {}
    print("[GPIO] Initializing GPIO pins for LEDs...")
    for color, pin_num in LED_MAPPING.items():
        try:
            gpio_objects[color] = GPIO(pin_num, "out")
            gpio_objects[color].write(False) # Start with all LEDs off
        except Exception as e:
            print(f"[ERROR] Failed to initialize GPIO {pin_num} for {color}: {e}")
            # Return None if any GPIO fails, to halt the script.
            return None
    print("[GPIO] All LED pins initialized and set to OFF.")
    return gpio_objects

def capture_image_from_webcam():
    """Deletes old image and captures a new one."""
    if os.path.exists(IMAGE_FILE_PATH):
        try:
            os.remove(IMAGE_FILE_PATH)
        except OSError as e:
            print(f"[ERROR] Could not remove old image file: {e}")
            return None
            
    print(f"[CAMERA] Capturing image from {CAMERA_DEVICE}...")
    command = ["fswebcam", "-d", CAMERA_DEVICE, "-r", "640x480", "-S", "20", "--no-banner", IMAGE_FILE_PATH]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        if os.path.exists(IMAGE_FILE_PATH):
            print(f"[CAMERA] Image successfully saved to {IMAGE_FILE_PATH}")
            return IMAGE_FILE_PATH
        else:
            print("[ERROR] fswebcam ran but did not create a new image file.")
            return None
    except Exception as e:
        print(f"[ERROR] fswebcam failed: {e}")
        return None

def get_analysis_from_server(image_path):
    """Sends image to server and returns JSON response."""
    if not image_path: return None
    print(f"[AI] Sending '{os.path.basename(image_path)}' to DingaVision server...")
    try:
        with open(image_path, 'rb') as image_file:
            files_payload = {'file': (os.path.basename(image_path), image_file, 'image/jpeg')}
            response = requests.post(DINGA_VISION_URL, files=files_payload, timeout=45)
            response.raise_for_status()
            print("[AI] Successfully received response from server.")
            return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request to DingaVision server failed: {e}")
        return None

def main():
    """Main loop to capture, analyze, and act."""
    gpio_leds = setup_gpios()
    if not gpio_leds:
        print("Exiting due to GPIO setup failure. Check pin numbers and permissions.")
        sys.exit(1)

    try:
        while True:
            # 1. Sense: Capture the image
            captured_image_path = capture_image_from_webcam()
            
            # 2. If capture was successful, send it for analysis
            if captured_image_path:
                result = get_analysis_from_server(captured_image_path)
                
                # 3. Process the result
                if result and "error" not in result:
                    print("\n--- ANALYSIS RESULT ---")
                    caption = result.get('caption', '(No caption returned)')
                    commands = result.get('interpretation', ['None']) 
                    
                    print(f"Moondream Caption: '{caption}'")
                    print(f"Extracted Commands: {commands}\n")
                    
                    # 4. Act on the list of commands
                    # First, turn all LEDs off to reset the state for this cycle.
                    for led_obj in gpio_leds.values():
                        led_obj.write(False)

                    if not commands or commands[0] == "None":
                        print("ACTION: No specific LED command detected.")
                    elif commands[0] == "All Off":
                        print("ACTION: 'All Off' command detected. All LEDs are now off.")
                    else:
                        # Iterate through the list of commands found and turn on corresponding LEDs
                        for command in commands:
                            command_key = command.lower() # e.g. "red led"
                            if command_key in gpio_leds:
                                print(f"ACTION: '{command}' detected. Turning ON corresponding LED.")
                                gpio_leds[command_key].write(True)
                            else:
                                print(f"ACTION: Received unknown command '{command}', ignoring.")

            # Wait before the next cycle
            print("\n-------------------------------------------------")
            print(f"Cycle complete. Waiting 30 seconds before next capture...")
            print("-------------------------------------------------")
            time.sleep(30)

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    finally:
        print("Cleaning up GPIOs...")
        if 'gpio_leds' in locals() and gpio_leds:
            for led in gpio_leds.values():
                led.write(False) # Ensure all LEDs are off
                led.close()
        print("Script finished.")

if __name__ == "__main__":
    main()
