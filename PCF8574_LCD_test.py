import time
# Import the CharLCD class for I2C connection from RPLCD library
from RPLCD.i2c import CharLCD

# --- Configuration (MUST VERIFY/CHANGE THESE!) ---

# I2C Bus Number (Check /dev/ for i2c-N devices)
I2C_PORT = 3

# I2C Address of the LCD Backpack (Use 'sudo i2cdetect -y <port>' to find)
# Set this to the address of the LCD currently connected (e.g., 0x27)
LCD_ADDRESS = 0x27 # <--- !!! SET TO 0x27 for the original LCD !!!

# LCD Dimensions
LCD_COLS = 16
LCD_ROWS = 2

# I/O Expander Chip Type on the Backpack (PCF8574 is most common)
EXPANDER_CHIP = 'PCF8574'

# --- Initialize the LCD (Attempt 2: Trying Alternative Pin Map) ---
lcd = None # Initialize lcd variable outside try block
try:
    print(f"Initializing LCD (Alt Pin Map) at address {hex(LCD_ADDRESS)} on I2C bus {I2C_PORT}...")
    # *** MODIFIED INITIALIZATION BELOW ***
    # Using explicit pin mapping based on a common alternative wiring
    lcd = CharLCD(
        EXPANDER_CHIP,       # Expander chip type ('PCF8574')
        address=LCD_ADDRESS, # Your address (e.g., 0x27)
        port=I2C_PORT,       # Your port (e.g., 3)

        # --- Explicit Pin Mapping ---
        # Common alternative map found on many blue boards
        pin_rs=0,     # RS -> P0 (Common)
        pin_e=1,      # E  -> P1 (** Trying P1 instead of default P2 **)
        pin_rw=None,  # RW -> Assumed grounded (Set to pin number if controlled)
        pins_data=[4, 5, 6, 7], # D4-D7 -> P4-P7 (Common)
        pin_backlight=3, # Backlight -> P3 (Seems correct for your board)
        # --------------------------

        cols=LCD_COLS, # 16
        rows=LCD_ROWS, # 2
        backlight_enabled=True # Turn backlight on initially
    )
    print("LCD Initialized with custom pin map.")
    # *** END MODIFIED INITIALIZATION ***

    # --- Example Usage ---
    print("Running LCD test...")
    print("Adjust contrast pot now!")

    # Clear the display
    lcd.clear()
    time.sleep(1) # Pause after clear

    # Write line 1
    lcd.cursor_pos = (0, 0) # Row 0, Col 0
    lcd.write_string("Hello")
    time.sleep(0.5)

    # Write line 2
    lcd.cursor_pos = (1, 0) # Row 1, Col 0
    lcd.write_string("from GNL Project!")

    # Keep message displayed - adjust contrast during this time
    print("Message displayed. Keep adjusting contrast...")
    time.sleep(8) # Increased sleep time to adjust contrast

    # Example: Turn off backlight
    print("Turning backlight off...")
    lcd.backlight_enabled = False
    time.sleep(2)

    # Example: Turn on backlight
    print("Turning backlight on...")
    lcd.backlight_enabled = True
    time.sleep(2)

    # Example: Clear display before exiting
    print("Clearing display...")
    lcd.clear()
    time.sleep(1)

except Exception as e:
    print(f"\nError initializing or using LCD: {e}")
    print("Please check:")
    print(f"- Is the correct I2C bus ({I2C_PORT}) used?")
    print(f"- Is the correct I2C address ({hex(LCD_ADDRESS)}) used? (Run 'sudo i2cdetect -y {I2C_PORT}')>
    print(f"- Are the LCD connections (SDA, SCL, VCC, GND) correct and secure?")
    print(f"- Did you adjust the contrast potentiometer on the backpack?")
    print(f"- Are the required libraries (RPLCD, smbus2) installed?")
    # Display traceback for unexpected errors
    import traceback
    traceback.print_exc()


finally:
    # Optional: Cleanup - turn off backlight if LCD object exists
    if lcd:
        try:
            # Turn backlight off as a final step
            print("Turning backlight off in finally block.")
            lcd.backlight_enabled = False
            # You might also clear it if desired
            # lcd.clear()
        except Exception as e:
            print(f"Error during final cleanup: {e}")
    print("\nLCD test finished.")

