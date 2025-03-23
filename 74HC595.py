from periphery import GPIO
import time

# Define GPIO pins
DATA_PIN = 53
SHIFT_CLOCK_PIN = 52
LATCH_CLOCK_PIN = 54
OUTPUT_ENABLE_PIN = 55

# Initialize GPIOs
data = GPIO(DATA_PIN, "out")
shift_clock = GPIO(SHIFT_CLOCK_PIN, "out")
latch_clock = GPIO(LATCH_CLOCK_PIN, "out")
output_enable = GPIO(OUTPUT_ENABLE_PIN, "out")

# Enable outputs
output_enable.write(False)

def pulse(pin):
    pin.write(True)
    time.sleep(0.001)
    pin.write(False)
    time.sleep(0.001)

def shift_out(bits):
    for bit in bits:
        data.write(bit == '1')
        pulse(shift_clock)
    pulse(latch_clock)

def invert(bits):
    return ''.join('1' if b == '0' else '0' for b in bits)

while True:
    user_input = input("Enter a 10-bit binary number (e.g., 1011001101): ")
    if len(user_input) != 10 or any(c not in '01' for c in user_input):
        print("Invalid input. Please enter exactly 10 bits (0 or 1).")
        continue

    # Invert logic for active-low LED wiring
    inverted = invert(user_input)

    # Add 6 zero bits at the beginning (shifted in first)
    full_bits = '000000' + inverted

    # Shift MSB first
    shift_out(full_bits)
