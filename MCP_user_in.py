from smbus2 import SMBus
import time

# Define I2C bus and MCP4725 Address
I2C_BUS = 3  
DAC_ADDR = 0x60  

# Set the reference voltage (adjust if using 5V VDD)
VDD = 4.9  # Change to 5.0 if using a 5V system

def reset_dac():
    """Reset the DAC using General Call Reset (0x06)."""
    with SMBus(I2C_BUS) as bus:
        bus.write_byte(0x00, 0x06)  # General Call Reset command
    print("♻️ DAC Reset Sent")
    time.sleep(0.05)

def set_dac_voltage(voltage):
    """Convert voltage to DAC value and set the MCP4725 output."""
    if not 0 <= voltage <= VDD:
        print(f"⚠️ Voltage out of range! Must be between 0 and {VDD}V.")
        return

    # Convert voltage to 12-bit DAC value (0-4095)
    dac_value = int((voltage / VDD) * 4095)

    command_byte = 0x40  # Fast Mode Write
    high_byte = (dac_value >> 4) & 0xFF
    low_byte = (dac_value << 4) & 0xF0  # Lower 4 bits shifted

    with SMBus(I2C_BUS) as bus:
        bus.write_i2c_block_data(DAC_ADDR, command_byte, [high_byte, low_byte])
    
    print(f"✅ DAC set to {dac_value} ({voltage:.3f} V)")

# 🔹 Run User Input Mode
if __name__ == "__main__":
    reset_dac()  # Reset DAC at the start

    while True:
        try:
            # Ask user for a voltage instead of raw DAC value
            user_input = input(f"\nEnter voltage (0-{VDD}V) or 'q' to quit: ").strip()
            if user_input.lower() == 'q':
                print("🚪 Exiting...")
                break

            voltage = float(user_input)  # Convert input to float
            set_dac_voltage(voltage)

        except ValueError:
            print("❌ Invalid input! Please enter a voltage between 0 and", VDD, "V.")
