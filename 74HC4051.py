#!/usr/bin/env python3

import os
import time
import sys

# --- Configuration ---
# Map GPIO numbers to selector pins S0, S1, S2
SELECTOR_PINS = [64, 65, 66] # S0, S1, S2

# --- ADC Configuration (NEEDS VERIFICATION ON YOUR DEVICE) ---
ADC_IIO_DEVICE_NAME = "iio:device0" # Verify this device name
ADC_CHANNEL_NAME = "in_voltage0"    # Verify this channel name for ADC0/Pin 144
ADC_RAW_FILE = f"/sys/bus/iio/devices/{ADC_IIO_DEVICE_NAME}/{ADC_CHANNEL_NAME}_raw"

# --- ADC Parameters (NEEDS VERIFICATION FOR YOUR BOARD/SETUP) ---
ADC_VREF = 1.8  # Volts (Common for RV1106 SARADC)
ADC_RESOLUTION_BITS = 10 # (Common for RV1106 SARADC)
ADC_MAX_VALUE = (2**ADC_RESOLUTION_BITS) - 1 # e.g., 1023 for 10-bit

# --- GPIO Sysfs Helper Functions (Same as before) ---

def gpio_export(pin):
    if not isinstance(pin, int): pin = int(pin)
    path = f"/sys/class/gpio/export"
    if not os.path.exists(f"/sys/class/gpio/gpio{pin}"):
        try:
            with open(path, "w") as f: f.write(str(pin))
            # print(f"GPIO {pin} exported.") # Less verbose
            time.sleep(0.1)
        except PermissionError:
            print(f"Error: Permission denied to export GPIO {pin}. Try sudo.")
            sys.exit(1)
        except Exception as e:
            print(f"Error exporting GPIO {pin}: {e}")
            sys.exit(1)
    # else: print(f"GPIO {pin} already exported.") # Less verbose

def gpio_unexport(pin):
    if not isinstance(pin, int): pin = int(pin)
    path = f"/sys/class/gpio/unexport"
    if os.path.exists(f"/sys/class/gpio/gpio{pin}"):
        try:
            with open(path, "w") as f: f.write(str(pin))
        except Exception as e:
            print(f"Warning: Error unexporting GPIO {pin}: {e}")

def gpio_set_direction(pin, direction="out"):
    if not isinstance(pin, int): pin = int(pin)
    path = f"/sys/class/gpio/gpio{pin}/direction"
    if not os.path.exists(path):
        print(f"Error: GPIO {pin} direction file not found. Was export ok?")
        return False
    try:
        with open(path, "w") as f: f.write(direction)
        return True
    except PermissionError:
        print(f"Error: Permission denied setting direction for GPIO {pin}.")
        return False
    except Exception as e:
        print(f"Error setting direction for GPIO {pin}: {e}")
        return False

def gpio_set_value(pin, value):
    if not isinstance(pin, int): pin = int(pin)
    if value not in [0, 1]: return False
    path = f"/sys/class/gpio/gpio{pin}/value"
    if not os.path.exists(path): return False
    try:
        with open(path, "w") as f: f.write(str(value))
        return True
    except Exception: # Catch broader errors on set_value
        return False

# --- 74HC4051 Control Function ---

def select_mux_channel(channel):
    """Sets the selector pins to choose the desired MUX channel (0-7)."""
    if not 0 <= channel <= 7:
        print(f"Error: Channel {channel} out of range (0-7).")
        return False

    s0_val = (channel >> 0) & 1
    s1_val = (channel >> 1) & 1
    s2_val = (channel >> 2) & 1

    print(f"Selecting channel {channel} (S2={s2_val}, S1={s1_val}, S0={s0_val})... ", end="")

    # Set GPIO values (assuming SELECTOR_PINS = [S0, S1, S2])
    if not gpio_set_value(SELECTOR_PINS[0], s0_val): return False # S0
    if not gpio_set_value(SELECTOR_PINS[1], s1_val): return False # S1
    if not gpio_set_value(SELECTOR_PINS[2], s2_val): return False # S2
    print("Done.")
    return True

# --- ADC Reading Function ---

def read_adc_voltage():
    """Reads the raw ADC value and converts it to voltage."""
    try:
        with open(ADC_RAW_FILE, "r") as f:
            raw_value_str = f.read().strip()
        raw_value = int(raw_value_str)

        # Convert raw value to voltage
        voltage = (raw_value / ADC_MAX_VALUE) * ADC_VREF
        print(f"Read ADC: Raw={raw_value}, Voltage={voltage:.3f}V")
        return voltage

    except FileNotFoundError:
        print(f"\nError: ADC raw file not found at '{ADC_RAW_FILE}'.")
        print("Please verify the ADC path configuration constants in the script.")
        return None
    except ValueError:
        print(f"\nError: Could not convert ADC raw value '{raw_value_str}' to integer.")
        return None
    except PermissionError:
         print(f"\nError: Permission denied reading ADC file '{ADC_RAW_FILE}'. Try sudo.")
         return None
    except Exception as e:
        print(f"\nError reading ADC: {e}")
        return None

# --- Main Program ---

if __name__ == "__main__":
    print("--- 74HC4051 MUX + ADC Read Script ---")
    print(f"Using GPIOs: S0={SELECTOR_PINS[0]}, S1={SELECTOR_PINS[1]}, S2={SELECTOR_PINS[2]}")
    print(f"Reading ADC from: {ADC_RAW_FILE}")
    print(f"Assuming Vref={ADC_VREF}V, Resolution={ADC_RESOLUTION_BITS}-bit")
    print("---")

    pins_to_manage = SELECTOR_PINS

    try:
        # Export and configure GPIOs
        print("Configuring GPIOs...")
        all_configured = True
        for pin in pins_to_manage:
            gpio_export(pin)
            if not gpio_set_direction(pin, "out"):
                all_configured = False; break

        if not all_configured:
            print("GPIO configuration failed. Exiting.")
            # Cleanup already exported pins before exiting
            raise RuntimeError("GPIO setup failed") # Jump to finally block

        print("GPIOs configured.")
        print("---")

        while True:
            try:
                user_input = input("Enter MUX channel (0-7) or Q to quit: ").strip().lower()

                if user_input == 'q':
                    break

                channel = int(user_input)
                if not 0 <= channel <= 7:
                    print("Invalid channel number. Please enter 0-7.")
                    continue

                # Select the MUX channel
                if not select_mux_channel(channel):
                     print("Error setting MUX channel GPIOs.")
                     continue # Ask for input again

                # Allow MUX and ADC input to settle
                time.sleep(0.1)

                # Read the ADC voltage
                voltage = read_adc_voltage()
                if voltage is None:
                    print("Failed to read voltage. Check ADC path/permissions.")
                    # Optionally break or continue based on desired error handling
                    # break

                print("-" * 20) # Separator

            except ValueError:
                print("Invalid input. Please enter a number (0-7) or Q.")
            except EOFError: # Handle Ctrl+D
                 print("\nEOF detected. Exiting.")
                 break

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Cleaning up...")
    except Exception as e:
         print(f"\nAn unexpected error occurred: {e}")
    finally:
        # Unexport GPIOs on exit
        print("\nUnexporting GPIOs...")
        for pin in pins_to_manage:
            gpio_unexport(pin)
        print("Cleanup complete. Exiting.")
