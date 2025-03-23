from periphery import GPIO
import time

# Define the output pin (change if needed)
LED_PIN = 55  

# Initialize the GPIO pin as output
led = GPIO(LED_PIN, "out")

try:
    while True:
        # Turn LED on
        led.write(True)
        print("💡 LED ON")
        time.sleep(1)

        # Turn LED off
        led.write(False)
        print("💡 LED OFF")
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping LED control.")
    led.write(False)  # Ensure LED is turned off on exit

finally:
    led.close()  # Clean up the GPIO pin
