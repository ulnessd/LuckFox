#!/usr/bin/env python3
# oled_status_display.py
# Runs on the LuckFox with the OLED display.
# Subscribes to MQTT status messages and updates the OLED.

import paho.mqtt.client as mqtt
import time
import json
import sys
import socket # For gaierror
from datetime import datetime # Added for logging timestamps if needed

# Luma.OLED specific imports
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306 # Or sh1106, or other as per your display
from luma.core.render import canvas
from PIL import ImageFont

# --- Configuration ---
BROKER_IP = "127.0.0.1"  # Broker is running on this same machine (luckfox-206)
MQTT_PORT = 1883
STATUS_TOPIC_WILDCARD = "luckfox/+/status"  # Subscribe to status from all boards

# OLED Configuration
try:
    I2C_PORT = 3  # Confirm this is correct for your LuckFox board
    I2C_ADDRESS = 0x3C # Common address for SSD1306/SH1106 OLEDs
    OLED_WIDTH = 128
    OLED_HEIGHT = 64 # Common for 0.96" or 1.3" OLEDs

    serial_interface = i2c(port=I2C_PORT, address=I2C_ADDRESS)
    # Ensure ssd1306 is the correct device for your OLED. Others: sh1106, etc.
    oled_device = ssd1306(serial_interface, width=OLED_WIDTH, height=OLED_HEIGHT) 
    
    # Load a font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    # Adjust font sizes as needed
    status_font_size = 8 # Smaller font to fit more info
    title_font_size = 10
    status_font = ImageFont.truetype(font_path, status_font_size)
    title_font = ImageFont.truetype(font_path, title_font_size)
    oled_available = True
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] OLED display initialized successfully.")
except FileNotFoundError:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Font file not found at {font_path}. Using default system font.")
    # Fallback to a very basic default font if TTF is not found
    # This ensures the script can run, but the display will be less pretty.
    status_font = ImageFont.load_default() 
    title_font = ImageFont.load_default() 
    oled_available = True # Still attempt to use OLED with default font
    # If oled_device failed above due to other reasons, this won't fix it.
    if 'oled_device' not in locals() or oled_device is None: # Check if oled_device was initialized
        try: # Attempt to initialize oled_device again if font was the only issue (unlikely for FileNotFoundError)
             serial_interface = i2c(port=I2C_PORT, address=I2C_ADDRESS)
             oled_device = ssd1306(serial_interface, width=OLED_WIDTH, height=OLED_HEIGHT)
        except Exception as e_oled_retry:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] OLED retry failed: {e_oled_retry}")
            oled_available = False
            oled_device = None
except Exception as e:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Error initializing OLED display: {e}")
    print("        Ensure I2C is enabled, correct port/address is used, and luma.oled/Pillow are installed.")
    oled_available = False
    oled_device = None

# --- Data Storage & Display Logic ---
board_statuses = {}  # Dictionary to store the latest status from each board
# Adjust MAX_LINES based on font and desired info. Each board might take more space now.
# If status_font_size is 8, line height is ~9-10px.
# Title line ~12px. Yellow band might be ~16px.
# Available height for data lines = 64 - 16 (approx) = 48px. So maybe 4 lines.
MAX_LINES_ON_OLED = 4 
YELLOW_BAND_HEIGHT = 16 # Approx. height of the yellow band in pixels (adjust if known)
STALE_DATA_THRESHOLD_S = 90 # Consider data stale after this many seconds

def update_oled_display():
    if not oled_available or not oled_device:
        return

    # The `with canvas(oled_device) as draw:` block automatically handles
    # creating a drawing surface and clearing the display for each redraw.
    with canvas(oled_device) as draw:
        y_offset = 0
        # Draw title, hopefully within the yellow band if present at the top
        draw.text((0, y_offset), "LuckFox Rack Status:", fill="white", font=title_font)
        
        # Start drawing actual data lines below the yellow band
        y_offset = YELLOW_BAND_HEIGHT 
        
        # Sort by board ID for consistent display order
        sorted_board_ids = sorted(board_statuses.keys())
        current_time_for_stale_check = time.time()
        lines_drawn = 0

        for board_id_full in sorted_board_ids:
            if lines_drawn >= MAX_LINES_ON_OLED:
                break 

            status = board_statuses.get(board_id_full, {})
            payload_timestamp_str = status.get("timestamp", "??:??:??") # From reporter
            local_rx_timestamp = status.get("timestamp_local_rx", 0) # When this listener got it

            # Extract HH:MM from "YYYY-MM-DD HH:MM:SS"
            try:
                time_hh_mm = payload_timestamp_str.split(" ")[1][:5] # Gets HH:MM
            except (IndexError, AttributeError): # Handle if timestamp is not a string or malformed
                time_hh_mm = "??:??"

            # Shorten board_id for display. Assumes IDs like "luckfox-200" or "200"
            id_parts = board_id_full.split('-')
            board_id_short = id_parts[-1] if len(id_parts) > 1 and id_parts[-1].isdigit() else board_id_full[:3]
            # If BOARD_ID in reporter is just "200", this will make it "200" via the else part. Good.

            if current_time_for_stale_check - local_rx_timestamp > STALE_DATA_THRESHOLD_S:
                display_line = f"{board_id_short}: STALE - {time_hh_mm}" 
            else:
                temp = status.get("temp_c", "??")
                mem_str = status.get("mem_usage_str", "??/??M") # e.g., "44M/246M"
                mem_used = mem_str.split('/')[0] if '/' in mem_str else "?M"
                if mem_used.endswith("M"): mem_used = mem_used[:-1] # Strip 'M' for space, e.g., "44"

                uptime = status.get("uptime_h", "??")
                
                # Format: ID T:Temp M:UsedMem U:UptimeH HH:MM
                display_line = f"{board_id_short} T:{temp} M:{mem_used} U:{uptime}h {time_hh_mm}"
                
                # Check line length (optional, for very small displays/large fonts)
                # text_width, _ = draw.textsize(display_line, font=status_font)
                # if text_width > OLED_WIDTH:
                #     display_line = f"{board_id_short} T:{temp} M:{mem_used} U:{uptime}h" # Shorter version

            draw.text((0, y_offset), display_line, fill="white", font=status_font)
            y_offset += status_font_size + 2 # Spacing for next line (font_size + 2px gap)
            lines_drawn +=1
            
        if not lines_drawn and sorted_board_ids: # All data was stale
            draw.text((0, y_offset), "All data stale...", fill="white", font=status_font)
        elif not sorted_board_ids: # No data received yet
            draw.text((0, y_offset), "Waiting for data...", fill="white", font=status_font)

# --- MQTT Callbacks (on_connect, on_disconnect, on_message) ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] Successfully connected to MQTT Broker at {BROKER_IP}")
        client.subscribe(STATUS_TOPIC_WILDCARD)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] Subscribed to topic: {STATUS_TOPIC_WILDCARD}")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Failed to connect to MQTT Broker, return code {rc} ({mqtt.connack_string(rc)})")

def on_disconnect(client, userdata, rc, *args):
    reason_string = rc
    if hasattr(rc, 'getName'): reason_string = rc.getName()
    elif isinstance(rc, int): reason_string = f"Code: {rc}"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [WARNING] Disconnected from MQTT Broker. Reason: {reason_string}")
    if args: print(f"  Extra disconnect arguments/properties: {args}")

def on_message(client, userdata, msg):
    global board_statuses
    try:
        payload_str = msg.payload.decode()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [DEBUG] Received on '{msg.topic}': {payload_str}")
        data = json.loads(payload_str)
        board_id = data.get("board_id", msg.topic.split('/')[1]) # Get board ID
        data["timestamp_local_rx"] = time.time() # Add local receive timestamp for staleness check
        board_statuses[board_id] = data
        update_oled_display() # Update display whenever a new message arrives
    except json.JSONDecodeError:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Received non-JSON message on topic {msg.topic}: {msg.payload.decode(errors='replace')}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Error processing message from topic {msg.topic}: {e}")

# --- Main ---
if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [IMPORTANT] OLED Status Display Manager starting...")

    if not oled_available:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] OLED not initialized properly. Script will run as a console listener only.")

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="OLED_Status_Display_Manager_Unique") # Ensure unique client ID
    
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(BROKER_IP, MQTT_PORT, 60)
    except ConnectionRefusedError:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Connection refused. Is MQTT broker at {BROKER_IP} running?")
        sys.exit(1)
    except socket.gaierror:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Broker IP {BROKER_IP} could not be resolved.")
        sys.exit(1)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] Could not connect to MQTT broker: {e}")
        sys.exit(1)

    update_oled_display() # Initial display (likely "Waiting for data...")

    try:
        mqtt_client.loop_forever() 
    except KeyboardInterrupt:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] OLED Manager stopping by user request...")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] An error occurred in the OLED Manager main loop: {e}")
    finally:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] Shutting down OLED Manager...")
        if mqtt_client.is_connected():
            mqtt_client.disconnect()
        if oled_available and oled_device:
            try:
                oled_device.clear()
                oled_device.hide() 
            except Exception as e_oled_clear:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] Error clearing/hiding OLED: {e_oled_clear}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] OLED Manager fully stopped.")
        # If you had a shared logger: logger.write_report()

