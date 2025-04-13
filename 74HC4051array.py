import os
import time
import sys
import math # For isnan

# --- Configuration ---
NUM_CHANNELS = 8
SELECTOR_PINS = [64, 65, 66] # S0, S1, S2 (Verify mapping: 64->S0, 65->S1, 66->S2)

# --- ADC Configuration (NEEDS VERIFICATION ON YOUR DEVICE) ---
ADC_IIO_DEVICE_NAME = "iio:device0" # Verify this device name (ls /sys/bus/iio/devices/)
ADC_CHANNEL_NAME = "in_voltage0"    # Verify this channel name for ADC0/Pin 144
ADC_RAW_FILE = f"/sys/bus/iio/devices/{ADC_IIO_DEVICE_NAME}/{ADC_CHANNEL_NAME}_raw"

# --- ADC Parameters (NEEDS VERIFICATION FOR YOUR BOARD/SETUP) ---
ADC_VREF = 1.8  # Volts (Common for RV1106 SARADC)
ADC_RESOLUTION_BITS = 10 # (Common for RV1106 SARADC)
ADC_MAX_VALUE = (2**ADC_RESOLUTION_BITS) - 1 # e.g., 1023 for 10-bit

# --- Motion Detection Parameters (Tune these based on testing) ---
# Minimum absolute voltage difference from background to be considered significant
DIFFERENCE_THRESHOLD = 0.1 # Volts
# Minimum change in center-of-mass position to register as movement
POSITION_TOLERANCE = 0.5 # Units of sensor spacing (0.0 to 7.0)
# Delay between full scans of the array
SCAN_DELAY_S = 0.1 # Seconds (Controls update rate)
# Delay between selecting a MUX channel and reading ADC
ADC_SETTLE_DELAY_S = 0.05 # Seconds (Allow MUX and ADC input to settle)

# --- Global Variables ---
# Stores voltages from calibration
background_voltages = [0.0] * NUM_CHANNELS

# --- GPIO Sysfs Helper Functions (Corrected) ---

def gpio_export(pin):
    if not isinstance(pin, int): pin = int(pin)
    path = f"/sys/class/gpio/export"
    p_path = f"/sys/class/gpio/gpio{pin}"
    if not os.path.exists(p_path): # Check if NOT already exported
        try:
            with open(path, "w") as f:
                 f.write(str(pin))
            time.sleep(0.1) # Give sysfs time
            # *** ADDED explicit return True on successful export ***
            return True
        except PermissionError:
             print(f"Error: Permission denied to export GPIO {pin}. Try sudo.")
             sys.exit(1) # Exit on critical permission error
        except Exception as e:
            print(f"Error exporting GPIO {pin}: {e}")
            sys.exit(1) # Exit on other critical export errors
    else: # Pin already exported, consider this success
         # print(f"GPIO {pin} already exported.") # Optional print
         # *** ADDED explicit return True if already exported ***
         return True
    # Should not be reachable
    # return False

def gpio_unexport(pin):
    # Attempts to unexport, warns on failure but doesn't exit
    if not isinstance(pin, int): pin = int(pin)
    path = f"/sys/class/gpio/unexport"
    p_path = f"/sys/class/gpio/gpio{pin}"
    if os.path.exists(p_path):
        try:
            with open(path, "w") as f:
                f.write(str(pin))
            # print(f"GPIO {pin} unexported.") # Optional
        except Exception as e:
            print(f"Warning: Error unexporting GPIO {pin}: {e}")
    # else: print(f"GPIO {pin} not currently exported.") # Optional

def gpio_set_direction(pin, direction="out"):
    if not isinstance(pin, int): pin = int(pin)
    path = f"/sys/class/gpio/gpio{pin}/direction"
    if not os.path.exists(path):
        print(f"Error: GPIO {pin} direction file missing? Export ok?")
        return False
    try:
        with open(path, "w") as f:
            f.write(direction)
        return True # Return True on success
    except PermissionError:
        print(f"Error: Permission denied setting direction for GPIO {pin}.")
        return False
    except Exception as e:
        print(f"Error setting direction for GPIO {pin}: {e}")
        return False

def gpio_set_value(pin, value):
    if not isinstance(pin, int): pin = int(pin)
    if value not in [0, 1]:
        print(f"Error: Invalid value '{value}' for GPIO {pin}. Must be 0 or 1.")
        return False
    path = f"/sys/class/gpio/gpio{pin}/value"
    if not os.path.exists(path):
        print(f"Error: GPIO {pin} value file missing? Export ok?")
        return False
    try:
        with open(path, "w") as f:
            f.write(str(value))
        return True # Return True on success
    except PermissionError:
        print(f"Error: Permission denied setting value for GPIO {pin}.")
        return False
    except Exception as e:
        print(f"Error setting value for GPIO {pin}: {e}")
        return False

# --- 74HC4051 Control Function ---
def select_mux_channel(channel):
    """Sets the selector pins S0, S1, S2 based on channel number."""
    if not 0 <= channel < NUM_CHANNELS: return False
    s0, s1, s2 = (channel>>0)&1, (channel>>1)&1, (channel>>2)&1
    # Assumes SELECTOR_PINS = [S0_GPIO, S1_GPIO, S2_GPIO]
    ok = gpio_set_value(SELECTOR_PINS[0], s0) \
     and gpio_set_value(SELECTOR_PINS[1], s1) \
     and gpio_set_value(SELECTOR_PINS[2], s2)
    return ok

# --- ADC Reading Function ---
def read_adc_voltage():
    """Reads the raw ADC value and converts it to voltage."""
    try:
        with open(ADC_RAW_FILE, "r") as f:
            raw_value_str = f.read().strip()
        raw_value = int(raw_value_str)
        # Calculate voltage based on Vref and resolution
        voltage = (raw_value / ADC_MAX_VALUE) * ADC_VREF
        # Clamp voltage to reasonable bounds (optional, handles potential noise/spikes)
        # voltage = max(0.0, min(ADC_VREF * 1.05, voltage)) # Allow slightly over Vref?
        return voltage
    except FileNotFoundError:
         print(f"\nError: ADC file not found: {ADC_RAW_FILE}. Verify path.")
         return None # Indicate failure
    except PermissionError:
         print(f"\nError: Permission denied reading ADC file: {ADC_RAW_FILE}. Try sudo.")
         return None
    except ValueError:
         print(f"\nError: Non-integer value read from ADC file: '{raw_value_str}'.")
         return None
    except Exception as e:
        # print(f"\nADC Read Error: {e}") # Can be too verbose
        return None # Indicate failure

# --- Background Calibration Function ---
def calibrate_background():
    """Reads all channels once to establish baseline voltages."""
    global background_voltages
    print("\n--- Starting Background Calibration ---")
    print(f"Ensure ambient light is stable. Reading {NUM_CHANNELS} channels...")
    temp_readings = [0.0] * NUM_CHANNELS
    successful_reads = 0
    for ch in range(NUM_CHANNELS):
        if not select_mux_channel(ch):
            print(f"Error: Failed to select channel {ch} for calibration.")
            temp_readings[ch] = math.nan # Mark as invalid
            continue # Try next channel

        time.sleep(ADC_SETTLE_DELAY_S * 2) # Allow extra settling for calibration maybe
        voltage = read_adc_voltage()

        if voltage is not None:
            print(f"Channel {ch}: {voltage:.3f}V")
            temp_readings[ch] = voltage
            successful_reads += 1
        else:
            print(f"Error: Failed to read ADC for channel {ch} calibration.")
            temp_readings[ch] = math.nan # Mark as invalid

    if successful_reads == NUM_CHANNELS:
        background_voltages = temp_readings
        print("--- Background Calibration Complete ---")
        return True
    else:
        # Check if *any* reads failed
        nan_count = sum(1 for v in temp_readings if math.isnan(v))
        print(f"--- Calibration Failed: {nan_count} channel(s) could not be read. ---")
        # Decide if partial calibration is acceptable or not
        # For now, we require all channels to calibrate successfully.
        return False


# --- Main Program ---

if __name__ == "__main__":
    print("--- Photoresistor Array Motion Detection v2 ---")
    print(f"Reading ADC: {ADC_RAW_FILE} (Vref={ADC_VREF}V, {ADC_RESOLUTION_BITS}-bit)")
    print(f"Using GPIOs: S0={SELECTOR_PINS[0]}, S1={SELECTOR_PINS[1]}, S2={SELECTOR_PINS[2]}")
    print(f"Threshold={DIFFERENCE_THRESHOLD:.2f}V, Tolerance={POSITION_TOLERANCE:.2f}")
    print("---")

    pins_to_manage = SELECTOR_PINS
    gpios_successfully_configured = False # Flag to ensure cleanup only happens if setup starts ok

    try:
        # --- Export and configure GPIOs (Verbose Debugging Loop) ---
        print("Configuring GPIOs...")
        all_configured_ok = True # Track success within this block
        for pin in pins_to_manage:
            print(f"Processing GPIO {pin}...")
            # Export step (gpio_export handles exit on critical failure)
            if not gpio_export(pin):
                print(f"-> Failed to export GPIO {pin} (non-critical error?).") # Should only happen if already exported?
                # Let's assume if it returns False here, it's okay if it already existed
                pass # Treat as non-fatal for now, direction set will fail if needed

            # Direction step
            if not gpio_set_direction(pin, "out"):
                print(f"-> Failed to set direction for GPIO {pin}.")
                all_configured_ok = False
                break # Stop configuration on first failure

            print(f"-> GPIO {pin} configured successfully.")

        # Check if the configuration loop completed ok
        if not all_configured_ok:
            raise RuntimeError("GPIO setup failed during configuration loop")

        gpios_successfully_configured = True # Mark that setup passed this point
        print("GPIOs configured successfully.")
        # --- End GPIO Configuration ---


        # Perform initial calibration
        if not calibrate_background():
             raise RuntimeError("Initial background calibration failed")

        print("--- Starting Motion Detection Loop (Press Ctrl+C to exit) ---")

        # --- Main Scanning Loop ---
        previous_position = -1.0 # Keep track of the last valid position
        previous_position_was_valid = False # Flag to indicate if prev_pos is valid from last cycle

        while True:
            current_diffs = [0.0] * NUM_CHANNELS
            valid_readings_in_scan = 0

            # Scan all channels
            for ch in range(NUM_CHANNELS):
                if not select_mux_channel(ch):
                    # print(f"Warn: Failed to select channel {ch} during scan.") # Optional
                    current_diffs[ch] = math.nan
                    continue

                time.sleep(ADC_SETTLE_DELAY_S)
                voltage = read_adc_voltage()

                # Check if ADC read worked AND background for this channel is valid
                if voltage is not None and not math.isnan(background_voltages[ch]):
                    current_diffs[ch] = voltage - background_voltages[ch]
                    valid_readings_in_scan += 1
                else:
                    # Silently mark as invalid if ADC read failed or background was invalid
                    current_diffs[ch] = math.nan

            # --- Calculate Center of Mass ---
            weighted_sum = 0.0
            total_abs_diff = 0.0
            significant_change_detected = False

            for i, diff in enumerate(current_diffs):
                if math.isnan(diff): continue # Skip invalid readings from this scan

                abs_diff = abs(diff)
                # Check against threshold
                if abs_diff > DIFFERENCE_THRESHOLD:
                    significant_change_detected = True
                    weighted_sum += i * abs_diff
                    total_abs_diff += abs_diff

            # --- Determine Position and Direction ---
            direction = "---" # Default
            current_position = -1.0 # Reset current calculation for this cycle

            if significant_change_detected and total_abs_diff > 0: # Check total_abs_diff to avoid division by zero
                current_position = weighted_sum / total_abs_diff

                # *** UPDATED LOGIC: Only compare if previous position was valid ***
                if previous_position_was_valid:
                    if current_position > previous_position + POSITION_TOLERANCE:
                        direction = "RIGHT >>"
                    elif current_position < previous_position - POSITION_TOLERANCE:
                        direction = "<< LEFT"
                    # else: direction remains "---" (stationary or below tolerance)
                # else:
                    # This is the first detection in a sequence, direction remains "---"
                    # Or print "START"? Optional. For now, first detection shows no direction.
                    pass

                # Update state for the *next* cycle's comparison
                previous_position = current_position
                previous_position_was_valid = True
            else:
                 # No significant change detected in this scan
                 # Mark previous position as invalid for the next cycle's comparison
                 previous_position_was_valid = False
                 # Keep previous_position holding the last known value? Or reset?
                 # Let's keep it but rely on the flag. Resetting could be `previous_position = -1.0`


            # --- Print Output ---
            # Create position string with conditional formatting
            pos_str = f"{current_position:.2f}" if current_position >= 0 else "---"
            # Now print using the pre-formatted string
            print(f"\rDirection: {direction.ljust(10)} (Pos: {pos_str.rjust(7)})   ", end="")


            # Wait before next scan cycle
            time.sleep(SCAN_DELAY_S)
        # --- End Main Scanning Loop ---

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Cleaning up...")
    except RuntimeError as e: # Catch specific setup/calibration errors
        print(f"\nRuntime Error: {e}")
    except Exception as e: # Catch other unexpected errors
         print(f"\nAn unexpected error occurred: {e}")
         import traceback
         traceback.print_exc() # Print full traceback for unexpected errors
    finally:
        # --- Cleanup: Always Attempt Unexport ---
        print("\nUnexporting GPIOs...")
        # Attempt to unexport all managed pins only if setup got far enough
        # to potentially export them.
        # Using 'gpios_successfully_configured' flag set after successful loop.
        if gpios_successfully_configured:
             for pin in pins_to_manage:
                 gpio_unexport(pin)
        else:
            print("(Skipping unexport as GPIO setup may not have completed)")
        print("Cleanup complete. Exiting.")
