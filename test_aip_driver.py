import time
import AiP31068_LCD_driver # Import the NEW driver class

# --- Configuration ---
I2C_PORT = 3
LCD_ADDRESS = 0x3E # The 7-bit address for the Waveshare module

# --- Main ---
mylcd = None # Define outside try block for finally
if __name__ == '__main__':
    print("Initializing LCD using AiP31068_LCD_driver...")
    try:
        # Initialize the LCD object from the new driver
        mylcd = AiP31068_LCD_driver.AiP31068_LCD_driver(addr=LCD_ADDRESS, port=I2C_PORT, rows=2)
        print("LCD Initialized.")

        print("Running LCD test...")
        print("Adjust contrast pot if needed (though might not be present/used)...")

        # Display line 1
        mylcd.display_string("Waveshare Test", 1) # Write to line 1

        # Display line 2
        mylcd.display_string("Hello LuckFox!", 2) # Write to line 2

        print("Message displayed.")
        time.sleep(5)

        # Test clear
        print("Clearing display...")
        mylcd.clear()
        time.sleep(1)

        # Test cursor positioning and individual chars
        mylcd.setCursor(0, 0)
        mylcd.printout("Line 1 Test")
        mylcd.setCursor(5, 1) # Col 5 on Line 2
        mylcd.printout("Test 2")
        time.sleep(5)

        # Optional: Test experimental backlight control
        # print("Testing experimental backlight off...")
        # mylcd.backlight_off()
        # time.sleep(3)
        # print("Testing experimental backlight on...")
        # mylcd.backlight_on()
        # time.sleep(3)

        mylcd.clear()


    except FileNotFoundError:
        print(f"Error: I2C bus {I2C_PORT} not found. Check bus number and enable I2C.")
    except OSError as e:
        if e.errno == 121: # Remote I/O error (No ACK)
             print(f"Error: No device responded at address {hex(LCD_ADDRESS)} on bus {I2C_PORT}.")
             print("Check address, wiring, and power.")
        else:
             print(f"An OS error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
         print("\nLCD test finished.")
         if mylcd:
             mylcd.close() # Close the bus
