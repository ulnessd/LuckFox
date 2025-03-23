from smbus2 import SMBus
import time

# Define I2C bus and MCP4725 Address
I2C_BUS = 3  # Adjust based on your setup
DAC_ADDR = 0x60  # Change to 0x61 if A0 is tied to VDD

def reset_dac():
    """Reset the DAC using General Call Reset (0x06)."""
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(0x00, 0x06)  # General Call Reset command
    print("♻️ DAC Reset Sent")
    time.sleep(0.05)  # Allow time for reset

def set_dac(value):
    """Set the MCP4725 DAC output (12-bit, 0-4095)."""
    if not 0 <= value <= 4095:
        raise ValueError("DAC value must be between 0 and 4095.")

    command_byte = 0x40  # Fast Mode Write Command (Volatile Memory Only)
    high_byte = (value >> 4) & 0xFF
    low_byte = (value << 4) & 0xF0  # Lower 4 bits shifted

    with SMBus(I2C_BUS) as bus:
        bus.write_i2c_block_data(DAC_ADDR, command_byte, [high_byte, low_byte])
    
    print(f"✅ DAC set to {value} ({(value/4095) * 4.9:.2f} V)")

# Run the test
if __name__ == "__main__":
    reset_dac()  # Reset the DAC before starting

    # Sweep DAC output in steps
    for v in [1, 500, 1000, 2000, 3000, 4000, 4095]:  
        set_dac(v)
        time.sleep(5)  # Short delay between updates

