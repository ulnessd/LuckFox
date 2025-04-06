import serial
import time
import sys

# --- Configuration ---
# IMPORTANT: Verify these are correct for LuckFox UART3
SERIAL_PORT = "/dev/ttyS3" 
RX_PIN_INFO = "UART3_RX (Pin 57)" 
TX_PIN_INFO = "UART3_TX (Pin 56)"
BAUD_RATE = 9600
# ---------------------

print(f"--- LuckFox UART Loopback Test ---")
print(f"Port: {SERIAL_PORT}, Baud: {BAUD_RATE}")
print(f"Connect output of TX circuit (from {TX_PIN_INFO})")
print(f"to input of RX circuit.")
print(f"Connect output of RX circuit to {RX_PIN_INFO}.")
print("Ensure circuits have +/-9V power and common GND with LuckFox.")
print("Ensure DTR/RTS are NOT asserted initially by external factors (circuits don't use them).")

# Test data to send
test_string = "GNL\r\n"
test_data = test_string.encode('ascii')

ser = None # Initialize ser variable
success = False
try:
    # Open the serial port (8N1 is default)
    ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUD_RATE, timeout=1.0) # 1 second read timeout
    print(f"\nSerial port {ser.name} opened.")

    # Reset buffers just in case
    time.sleep(0.1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print("Input/Output buffers flushed.")
    
    # Assert DTR/RTS? Probably NOT needed for loopback, 
    # but keep for reference if direct connection fails later.
    # ser.dtr = True 
    # ser.rts = True
    # print("DTR/RTS Asserted (if uncommented)")
    
    time.sleep(0.2) # Short delay before sending
    
    # --- Send Data ---
    print(f"\nSending {len(test_data)} bytes: {test_data}")
    bytes_sent = ser.write(test_data)
    if bytes_sent != len(test_data):
        print(f"Warning: Only {bytes_sent} out of {len(test_data)} bytes sent.")
    ser.flush() # Ensure data is physically sent
    print("Send complete.")

    # --- Receive Data ---
    # Add a small delay to allow data to travel through loopback circuit
    # May need adjustment depending on circuit/system latency
    loopback_delay = 0.1 
    print(f"Waiting {loopback_delay}s for loopback...")
    time.sleep(loopback_delay)

    print(f"Attempting to read {len(test_data)} bytes back...")
    received_bytes = ser.read(len(test_data))
    
    # --- Verification ---
    print(f"\nReceived {len(received_bytes)} bytes: {received_bytes}")
    
    if received_bytes == test_data:
        print("\n*** SUCCESS: Received data matches sent data! ***")
        success = True
    else:
        print("\n*** ERROR: Received data does NOT match sent data! ***")
        print(f"Sent    : {test_data}")
        print(f"Received: {received_bytes}")
        # Try reading any remaining data in buffer
        time.sleep(0.1)
        extra_bytes = ser.read(ser.in_waiting or 100)
        if extra_bytes:
            print(f"Extra data received: {extra_bytes}")

except serial.SerialException as e:
    print(f"\nSerial Port Error: {e}")
    # Add permission hint etc. if needed
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")

finally:
    if ser and ser.is_open:
        # De-assert DTR/RTS if they were asserted
        # ser.dtr = False
        # ser.rts = False 
        ser.close()
        print(f"\nSerial port {ser.name} closed.")
    else:
        print("\nSerial port was not opened or already closed.")

print(f"\nLoopback Test { 'Completed Successfully' if success else 'Failed' }.")
