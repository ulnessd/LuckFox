# led_sequencer.py
# Fetches a timed sequence from a webpage and controls LEDs.
# Includes robust initialization and a startup self-test.

import subprocess
import time
from periphery import GPIO
import sys

# --- Configuration ---
# GPIO pin numbers must match the Linux system GPIO numbers for your physical pins.
LED_PINS = {
    "Red": 55,
    "Blue": 54,
    "Green": 53,
    "Yellow": 52
}
WEBPAGE_URL = "https://www.darinulness.com/teaching/luckfox-microcontroller-laboratory/linksledtestpage"

# --- GPIO Functions ---
def initialize_gpios():
    """Initialize GPIO pins as outputs with error handling for each pin."""
    led_objects = {}
    print("[INFO] Initializing GPIO pins...")
    for name, pin in LED_PINS.items():
        try:
            led_objects[name] = GPIO(pin, "out")
            led_objects[name].write(False) # Ensure LED is off initially
            print(f"  - {name} LED on GPIO {pin} initialized.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize {name} LED on GPIO {pin}: {e}")
            print("        Please check pin number and permissions (user may need to be in 'gpio' group).")
    return led_objects

def test_leds(leds):
    """Blinks each LED once at startup to confirm functionality."""
    if not leds:
        print("[WARN] No LEDs were initialized, skipping test.")
        return
    print("\n[INFO] Starting LED self-test...")
    try:
        for name, gpio in leds.items():
            print(f"  - Testing {name} LED...")
            gpio.write(True)
            time.sleep(0.85)
            gpio.write(False)
            time.sleep(0.4)
        print("[INFO] LED self-test complete.\n")
    except Exception as e:
        print(f"[ERROR] An error occurred during LED self-test: {e}")

def set_leds(states, led_objects):
    """Sets the state of all LEDs based on a list of 'on'/'off' strings."""
    # Ensure we have the same number of states as LEDs
    if len(states) != len(led_objects):
        print(f"[WARN] Mismatch between number of states ({len(states)}) and LEDs ({len(led_objects)}).")
        return
        
    for led_name, state_str in zip(led_objects.keys(), states):
        try:
            is_on = state_str.strip().lower() == "on"
            led_objects[led_name].write(is_on)
        except KeyError:
            print(f"[WARN] LED name '{led_name}' not found in initialized GPIOs.")
        except Exception as e:
            print(f"[ERROR] Could not set state for {led_name}: {e}")

# --- Web Fetching and Parsing ---
def fetch_sequence():
    """Fetches and parses the LED sequence from the webpage."""
    print(f"[INFO] Fetching sequence from {WEBPAGE_URL}...")
    try:
        result = subprocess.run(
            ["links", "-dump", WEBPAGE_URL],
            capture_output=True, text=True, check=True
        )
    except FileNotFoundError:
        print("[ERROR] 'links' command not found. Please install with 'sudo apt install links'.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to fetch webpage: {e}")
        return None

    lines = result.stdout.splitlines()
    sequence = []
    found_sequence_header = False
    
    for line in lines:
        line = line.strip()
        
        # Start parsing only after the header is found
        if "LED Sequence Code" in line:
            found_sequence_header = True
            continue
        
        if not found_sequence_header or not line:
            continue
            
        if line.upper().endswith("END"):
            sequence.append(("END", []))
            break # Stop parsing after END
            
        parts = line.split(",")
        if parts[0].isdigit() and len(parts) == 5:
            try:
                t = int(parts[0])
                states = parts[1:] # e.g., ["off", "on", "on", "off"]
                sequence.append((t, states))
            except ValueError:
                print(f"[WARN] Skipping malformed line: {line}")
                continue
                
    if sequence:
        print("[INFO] Successfully parsed sequence.")
    else:
        print("[WARN] No valid sequence data found on webpage.")

    return sequence

# --- Main Program Logic ---
def run_sequence(seq, led_objects):
    """Executes a parsed sequence of LED states and delays correctly."""
    # The sequence is a list of tuples: (timestamp, [states])
    
    # Iterate through the sequence using an index
    for i, entry in enumerate(seq):
        current_time, current_states = entry

        # Check for the end-of-sequence marker
        if current_time == "END":
            print("Sequence complete. Waiting before re-fetching...")
            # The line below was removed to hold the last state.
            # set_leds(["off", "off", "off", "off"], led_objects) 
            return # Exit the function, leaving LEDs in their last set state.

        # --- This is the new logic ---
        # 1. SET the LEDs to the current state immediately
        set_leds(current_states, led_objects)
        
        # 2. Determine how long to HOLD this state by looking at the next event
        hold_duration = 0
        if i + 1 < len(seq): # Check if there is a next entry
            next_entry = seq[i+1]
            # If the next step is END, hold for a default time
            if next_entry[0] == "END":
                hold_duration = 0.5 
            else:
                next_time = next_entry[0]
                hold_duration = next_time - current_time
        else:
            # This is the very last state in the sequence before the (missing) END tag
            hold_duration = 0.5 # Hold the last state for 2 seconds

        # 3. PRINT what we just did and how long we will wait
        print(f"[{current_time:>3}s] Set states: {current_states}. Holding for {hold_duration:.1f} sec...")
        
        # 4. WAIT for the calculated duration
        time.sleep(max(hold_duration, 0))

def main():
    """Main execution loop."""
    leds = initialize_gpios()
    # If initialization failed for some LEDs, leds dict will be smaller or empty
    if len(leds) != len(LED_PINS):
        print("[FATAL] Not all LEDs could be initialized. Please check errors above. Exiting.")
        sys.exit(1)
        
    test_leds(leds)
    
    try:
        print("Starting LED sequence loop (Ctrl+C to stop)...")
        while True:
            sequence = fetch_sequence()
            if not sequence:
                print("Retrying in 10 seconds...")
                time.sleep(10)
                continue
                
            run_sequence(sequence, leds)
            time.sleep(5)  # Delay before fetching the sequence again

    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        print("Cleaning up: Turning off all LEDs and closing GPIOs...")
        for gpio in leds.values():
            try:
                gpio.write(False)
                gpio.close()
            except Exception:
                pass # Ignore errors if pin was already closed or failed to init

if __name__ == "__main__":
    main()
