import serial
import time
import sys
import select # For non-blocking input check
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont
import os # To check if running in graphical environment for plotting display

# Attempt to import matplotlib, handle if not installed
try:
    import matplotlib
    # Check if running in a headless environment, use Agg backend for saving PNG
    # Check DISPLAY environment variable is usually reliable
    if os.environ.get('DISPLAY', '') == '': 
        print("Matplotlib loading...this could take some time.")
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib_available = True
except ImportError:
    print("Warning: Matplotlib library not found. Plotting will be disabled.")
    print("Install using: pip install matplotlib")
    matplotlib_available = False

# --- Configuration ---
# Serial Port (Setra Balance)
SERIAL_PORT = "/dev/ttyS3" 
BAUD_RATE = 300 
DATA_BITS = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOP_BITS = serial.STOPBITS_ONE
PORT_TIMEOUT = 0.1 
CMD_QUERY = b'#'
CMD_TARE = b'$t'
READ_TERMINATOR = b'\r\n' 
RESPONSE_TIMEOUT = 5.0 

# OLED Display (I2C)
I2C_PORT = 3
I2C_ADDRESS = 0x3C
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SIZE = 18 
OLED_UPDATE_INTERVAL = 1.0 # Seconds between weight queries/updates

# Recording / Plotting
PLOT_FILENAME = "evaporation_plot.png"

# --- Helper Functions ---

def send_command_no_echo(serial_object, command_bytes):
    """Sends command bytes directly. Returns True on success."""
    # (Same as before)
    if command_bytes == CMD_QUERY or command_bytes == CMD_TARE:
        full_command = command_bytes 
    else: 
        full_command = command_bytes + b'\r' 
        
    # print(f"Sending command: {full_command}") # Verbose
    try:
        serial_object.write(full_command)
        serial_object.flush()
        return True
    except Exception as e:
        print(f"\nError during write: {e}")
        return False

def query_and_parse_balance(serial_object):
    """Sends Query, reads response, parses, returns weight float or None."""
    # (Same parsing logic as before)
    serial_object.reset_input_buffer()
    if not send_command_no_echo(serial_object, CMD_QUERY): return None
    original_timeout = serial_object.timeout
    serial_object.timeout = RESPONSE_TIMEOUT
    response_bytes = ser.read_until(READ_TERMINATOR)
    serial_object.timeout = original_timeout
    if not response_bytes: return None
    try:
        response_string = response_bytes.decode('ascii', errors='ignore').strip()
        response_parts = response_string.split()
        if not response_parts: return None
        value_str = response_parts[0]
        if (value_str == '+' or value_str == '-') and len(response_parts) > 1:
            value_str += response_parts[1]
        try:
            weight = float(value_str)
            return weight
        except ValueError: return None
    except Exception: return None

def send_tare_command(serial_object):
    """Sends Tare command, returns True/False"""
    print("\nSending Tare command...")
    serial_object.reset_input_buffer()
    if not send_command_no_echo(serial_object, CMD_TARE): return False
    time.sleep(0.2)
    junk = serial_object.read(serial_object.in_waiting or 100)
    # if junk: print(f"--> Discarded post-tare data: {junk}") # Verbose
    print("Tare command sent.")
    return True

def update_oled(oled_device, oled_font, weight_value, is_recording_state):
    """Updates the OLED display with weight and recording status."""
    with canvas(oled_device) as draw:
        draw.rectangle(oled_device.bounding_box, outline="black", fill="black")
        
        rec_indicator = "*" if is_recording_state else "" # Add indicator if recording
        draw.text((0, 0), f"Setra Wt:{rec_indicator}", font=oled_font, fill="white")
        
        if weight_value is not None:
            weight_str = f"{weight_value: >8.3f} g" 
        else:
            weight_str = "---.--- g"
        draw.text((0, 25), weight_str, font=oled_font, fill="white")
        
        # Command instructions - include R/S now
        draw.text((0, 50), "T=Tare R=Rec S=Stop Q=Quit", font=ImageFont.truetype(FONT_PATH, 10), fill="white")

def plot_and_save(times, masses, filename="evaporation_plot.png"):
    """Generates and saves a plot of mass vs. time."""
    if not matplotlib_available:
        print("Plotting disabled: Matplotlib library not found.")
        return
    if not times or not masses or len(times) != len(masses):
        print("No data or mismatched data lengths, skipping plot.")
        return

    try:
        print(f"Generating plot with {len(times)} points...")
        plt.figure(figsize=(8, 6)) # Control figure size
        plt.plot(times, masses, marker='.', linestyle='-', markersize=4)
        plt.xlabel("Time (seconds)")
        plt.ylabel("Mass (g)")
        plt.title("Evaporation Kinetics")
        plt.grid(True)
        plt.tight_layout() # Adjust layout
        plt.savefig(filename)
        plt.close() # Close the plot figure to free memory
        print(f"Plot saved successfully to {filename}")
    except Exception as e:
        print(f"Error generating or saving plot: {e}")


# --- Main Execution ---
oled_serial = None
oled_device = None
ser = None
last_update_time = 0
current_weight = None
# Recording state variables
is_recording = False
recorded_times = []
recorded_masses = []
recording_start_time = 0

try:
    # Initialize OLED
    print("Initializing OLED display...")
    oled_serial = i2c(port=I2C_PORT, address=I2C_ADDRESS)
    oled_device = ssd1306(oled_serial)
    oled_font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    update_oled(oled_device, oled_font, None, is_recording) 
    print("OLED Initialized.")

    # Initialize Serial Port
    print(f"Initializing port {SERIAL_PORT} at {BAUD_RATE} 8N1...")
    ser = serial.Serial(
        port=SERIAL_PORT, baudrate=BAUD_RATE, bytesize=DATA_BITS,
        parity=PARITY, stopbits=STOP_BITS, timeout=PORT_TIMEOUT,
        xonxoff=False, rtscts=False, dsrdtr=False
    )
    print(f"Port {ser.name} opened.")
    time.sleep(0.5)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print("Buffers flushed. Starting loop...")
    print("Commands: T=Tare, R=Record, S=Stop, Q=Quit (Press Enter after command)")

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
                send_tare_command(ser)
                # Force immediate update after tare
                current_weight = query_and_parse_balance(ser) 
                update_oled(oled_device, oled_font, current_weight, is_recording)
                last_update_time = time.time()
            elif line == 'r':
                if not is_recording:
                    print("\n*** Starting Recording ***")
                    is_recording = True
                    recorded_times.clear()
                    recorded_masses.clear()
                    recording_start_time = time.time()
                    # Force immediate update to show recording indicator
                    current_weight = query_and_parse_balance(ser) 
                    update_oled(oled_device, oled_font, current_weight, is_recording)
                    last_update_time = time.time()
                else:
                    print("Already recording.")
            elif line == 's':
                if is_recording:
                    print("\n*** Stopping Recording ***")
                    is_recording = False
                    update_oled(oled_device, oled_font, current_weight, is_recording) # Update indicator
                    # Plot and save data
                    plot_and_save(recorded_times, recorded_masses, PLOT_FILENAME)
                else:
                    print("Not currently recording.")
            elif line: 
                 print(f"Unknown command: '{line}'. Use T, R, S, or Q.")

        # --- Query Balance and Update OLED/Record Periodically ---
        current_time = time.time()
        if current_time - last_update_time >= OLED_UPDATE_INTERVAL:
            new_weight = query_and_parse_balance(ser)
            
            # Update OLED if value changed or was None before
            if new_weight is not None or current_weight is not None:
                 if new_weight != current_weight:
                      current_weight = new_weight # Update stored weight only on change
                      update_oled(oled_device, oled_font, current_weight, is_recording)
            elif current_weight is not None: # If read failed, show dashes
                 update_oled(oled_device, oled_font, None, is_recording) 
                 current_weight = None # Mark last read failed
                 
            # Record data if recording is active and weight is valid
            if is_recording and current_weight is not None: # Use last known good weight
                elapsed_time = current_time - recording_start_time
                recorded_times.append(elapsed_time)
                recorded_masses.append(current_weight)
                # Optional: Print recorded point to console
                # print(f"Rec: {elapsed_time:.1f}s, {current_weight:.3f}g")

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
        try: oled_device.clear(); oled_device.hide(); print("OLED cleared.")
        except Exception as e: print(f"Error clearing OLED: {e}")
    if ser and ser.is_open:
        ser.close(); print(f"Serial port {ser.name} closed.")

    # If recording was stopped by Ctrl+C or error, try saving plot anyway
    if is_recording and recorded_times: # Check if recording was active and has data
         print("\nAttempting to save recorded data due to unexpected exit...")
         plot_and_save(recorded_times, recorded_masses, PLOT_FILENAME)
