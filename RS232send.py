import serial
import time
import sys

# --- Configuration ---
# IMPORTANT: Verify this is the correct device file for LuckFox UART3 TX (Pin 56)
SERIAL_PORT = "/dev/ttyS3" 
BAUD_RATE = 9600
# ---------------------

print(f"Attempting to open serial port {SERIAL_PORT} at {BAUD_RATE} baud.")
print("Connect Oscilloscope Probe to the OUTPUT of the 3-transistor circuit.")
print("Connect Oscilloscope Ground to the common GND.")
print("Ensure the +/-9V supply for the transistor circuit is ON.")

ser = None # Initialize ser variable
try:
    # Open the serial port (8 data bits, no parity, 1 stop bit is default)
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1 # Timeout for read operations (though we mainly write)
    )
    print(f"Serial port {ser.name} opened successfully.")
    
    # Optional: Some UARTs might benefit from a short pause after opening
    time.sleep(0.1)

    while True:
        try:
            # Get input from the user
            text_to_send = input("\nEnter text to transmit (or 'quit' to exit): ")

            if text_to_send.lower() == 'quit':
                break

            # Encode the string to bytes (ASCII is simple for testing)
            bytes_to_send = text_to_send.encode('ascii', errors='ignore')

            # Send the bytes
            bytes_sent = ser.write(bytes_to_send)
            print(f"Sent {bytes_sent} bytes: {bytes_to_send}")

            # Optionally send CR LF afterwards for better scope viewing / term compatibility
            ser.write(b'\r\n')
            print("Sent CR LF")

            # Ensure data is sent out physically
            ser.flush() 

        except KeyboardInterrupt:
            print("\nExiting loop.")
            break
        except EOFError: # Handle case where input stream closes unexpectedly
             print("\nInput stream closed, exiting.")
             break

except serial.SerialException as e:
    print(f"\nSerial Port Error: {e}")
    if "Permission denied" in str(e):
        print("--> Hint: You might need to run the script with 'sudo' or add your user")
        print(f"    to the 'dialout' group (e.g., sudo usermod -a -G dialout $USER)")
        print(f"    Remember to log out and back in after adding to the group.")
    elif "No such file or directory" in str(e):
         print(f"--> Hint: Check if '{SERIAL_PORT}' is the correct device name for UART3.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
    
finally:
    if ser and ser.is_open:
        ser.close()
        print(f"\nSerial port {ser.name} closed.")
    else:
        print("\nSerial port was not opened or already closed.")
