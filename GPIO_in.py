from periphery import GPIO
import time

# Define the input pin (change if needed)
INPUT_PIN = 54  

# Initialize the GPIO pin as input
input_gpio = GPIO(INPUT_PIN, "in")

try:
    print("Monitoring GPIO input... (Press Ctrl+C to stop)")
    while True:
        pin_state = input_gpio.read()
        
        if pin_state:
            print("📌 Pin is HIGH")
        else:
            print("📌 Pin is LOW")
        
        time.sleep(1.5)  # Adjust as needed

except KeyboardInterrupt:
    print("\nStopping GPIO input reading.")

finally:
    input_gpio.close()  # Clean up GPIO pin
