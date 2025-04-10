import serial
import time
import sys
import select # For non-blocking input check
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# --- Configuration ---
# Serial Port (Setra Balance)
SERIAL_PORT = "/dev/ttyS3"
BAUD_RATE = 300
DATA_BITS = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOP_BITS = serial.STOPBITS_ONE
PORT_TIMEOUT = 0.1 # *** ADDED THIS LINE *** Default timeout for basic reads
# ---------------------

# Commands (from manual Appendix II)
CMD_QUERY = b'#' # Immediate Print (for Weight/Mass)
CMD_TARE = b'$t' # Tare function
# Expected response termination
READ_TERMINATOR = b'\r\n' 
# Timeouts specific to response/echo reading
ECHO_TIMEOUT = 0.5 # Timeout specifically for reading echo (if used)
RESPONSE_TIMEOUT = 5.0 # Timeout for waiting for balance response data

# OLED Display (I2C)
I2C_PORT = 3
I2C_ADDRESS = 0x3C
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SIZE = 18 # Adjust as needed
OLED_UPDATE_INTERVAL = 1.0 # Seconds between weight queries

# --- Helper Functions ---

def send_command_no_echo(serial_object, command_bytes):
    """Sends command bytes directly. Returns True on success."""
    # Use bytes directly for command
    # Send exactly '#' or '$t' as per manual
    if command_bytes == CMD_QUERY or command_bytes == CMD_TARE:
        full_command = command_bytes 
    else: 
        # Fallback if other commands needed CR (unlikely for Setra based on manual)
        full_command = command_bytes + b'\r' 
        
    print(f"Sending command: {full_command}")
    try:
        serial_object.write(full_command)
        serial_object.flush()
        return True
    except serial.SerialException as e:
        print(f"\nSerial error during write: {e}")
        return False
    except Exception as e:
        print(f"\nUnexpected error during write: {e}")
        return False

# Note: Removing read_and_discard_echo as Setra likely doesn't echo input commands

def query_and_parse_balance(serial_object):
    """Sends Query command, reads response, parses, returns weight float or None."""
    # print("Querying balance...") # Less verbose in loop
    serial_object.reset_input_buffer() # Clear buffer before query
    if not send_command_no_echo(serial_object, CMD_QUERY):
        return None

    # --- Read Actual Response ---
    # print(f"Waiting for weight data (timeout={RESPONSE_TIMEOUT}s)...") # Less verbose
    original_timeout = serial_object.timeout
    serial_object.timeout = RESPONSE_TIMEOUT
    response_bytes = ser.read_until(READ_TERMINATOR)
    serial_object.timeout = original_timeout # Reset default timeout
    
    if not response_bytes:
        # print("--> Error: No response received (timeout).") # Less verbose
        return None
        
    # print(f"--> Received raw: {response_bytes}") # Less verbose
    try:
        response_string = response_bytes.decode('ascii', errors='ignore').strip()
        # print(f"--> Decoded: '{response_string}'") # Less verbose
        response_parts = response_string.split()
        if not response_parts: return None

        value_str = response_parts[0]
        if (value_str == '+' or value_str == '-') and len(response_parts) > 1:
            value_str += response_parts[1]

        # print(f"--> Extracted value string: '{value_str}'") # Less verbose
        
        try:
            weight = float(value_str)
            # Optionally grab units/stability if needed later
            return weight # Return the float value
            
        except ValueError:
            # print("--> Error: Could not convert value string to float.") # Less verbose
             if "HHH" in value_str: print("  (Balance overloaded)")
             if "LLL" in value_str: print("  (Balance pan off)")
             return None # Return None on conversion error

    except Exception as e:
        # print(f"--> Error processing response: {e}") # Less verbose
        return None

def send_tare_command(serial_object):
    """Sends Tare command, returns True/False"""
    print("\nSending Tare command...")
    serial_object.reset_input_buffer() # Clear buffer before command
    if not send_command_no_echo(serial_object, CMD_TARE):
        return False
    # Assume no specific response needed after Tare, but clear buffer just in case
    time.sleep(0.2) # Give balance time to process
    junk = serial_object.read(serial_object.in_waiting or 100)
    if junk: print(f"--> Discarded post-tare data: {junk}")
    print("Tare command sent.")
    return True

def update_oled(oled_device, oled_font, weight_value):
    """Updates the OLED display with the formatted weight."""
    with canvas(oled_device) as draw:
        draw.rectangle(oled_device.bounding_box, outline="black", fill="black") # Clear display
        draw.text((0, 0), "Setra Wt:", font=oled_font, fill="white")
        if weight_value is not None:
            # Format weight: Use enough precision (e.g., 3 decimals for Setra EL410S)
            # Right-align text potentially
            weight_str = f"{weight_value: >8.3f} g" 
        else:
            weight_str = "---.--- g"
        
        # Simple left alignment for now
        draw.text((0, 25), weight_str, font=oled_font, fill="white")
        draw.text((0, 50), "T=Tare Q=Quit", font=ImageFont.truetype(FONT_PATH, 12), fill="white")


# --- Main Execution ---
oled_serial = None
oled_device = None
ser = None
last_update_time = 0
current_weight = None # Store last successfully read weight

try:
    # Initialize OLED
    print("Initializing OLED display...")
    oled_serial = i2c(port=I2C_PORT, address=I2C_ADDRESS)
    oled_device = ssd1306(oled_serial)
    oled_font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    update_oled(oled_device, oled_font, None) 
    print("OLED Initialized.")

    # Initialize Serial Port
    print(f"Initializing port {SERIAL_PORT} at {BAUD_RATE} 8N1...")
    ser = serial.Serial(
        port=SERIAL_PORT, baudrate=BAUD_RATE, bytesize=DATA_BITS,
        parity=PARITY, stopbits=STOP_BITS, timeout=PORT_TIMEOUT, # Use defined PORT_TIMEOUT
        xonxoff=False, rtscts=False, dsrdtr=False
    )
    print(f"Port {ser.name} opened.")
    time.sleep(0.5)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print("Buffers flushed. Starting loop...")
    print("(Press Enter after T or Q. Updates happen automatically)")

    # Main Loop
    while True:
        # --- Check for User Input (Non-blocking) ---
        readable, _, _ = select.select([sys.stdin], [], [], 0) 
        if sys.stdin in readable:
            line = sys.stdin.readline().strip().lower()
            if line == 'q':
                print("Quit command received.")
                break
            elif line == 't':
                if send_tare_command(ser):
                     # Force an immediate update after tare attempt
                     current_weight = query_and_parse_balance(ser) 
                     update_oled(oled_device, oled_font, current_weight)
                     last_update_time = time.time() # Reset timer
                else:
                     print("Tare command failed to send.")
            # No need for M/W command, it happens automatically below
            elif line: # If user typed something other than q or t
                 print(f"Unknown command: '{line}'. Use T or Q.")

        # --- Query Balance and Update OLED Periodically ---
        current_time = time.time()
        if current_time - last_update_time >= OLED_UPDATE_INTERVAL:
            new_weight = query_and_parse_balance(ser)
            # Update OLED only if the value changed OR if the last reading failed
            if new_weight is not None or current_weight is not None: 
                 if new_weight != current_weight:
                      current_weight = new_weight
                      update_oled(oled_device, oled_font, current_weight)
            elif current_weight is not None: # If reading failed, but we had a previous value
                 # Optionally display dashes or keep last known value
                 update_oled(oled_device, oled_font, None) # Show dashes on error
                 current_weight = None # Mark that last read failed

            last_update_time = current_time

        # Prevent busy-looping
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nCtrl+C detected. Exiting.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
finally:
    # Clean up
    if oled_device:
        try:
            oled_device.clear()
            oled_device.hide()
            print("OLED cleared and hidden.")
        except Exception as e: print(f"Error clearing OLED: {e}")
    if ser and ser.is_open:
        ser.close()
        print(f"Serial port {ser.name} closed.")
