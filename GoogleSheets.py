import requests
import time
from datetime import datetime

# Google Form submission URL (Use the /formResponse URL)
form_url = "https://docs.google.com/forms/d/e/1FAIpQLSeYusTzxljbrujaQIgARJnTchzIvW5rIN_R5F1zjumtW_uesw/formResponse"

# Replace with your actual Google Form Entry IDs (Find these from the pre-filled link)
time_entry_id = "entry.1234567890"     # Replace with actual Time entry ID
voltage_entry_id = "entry.9876543210"  # Replace with actual ADC0 Voltage entry ID

# ADC File Directory
ADC_DIR = "/sys/bus/iio/devices/iio:device0"

# Function to read ADC values
def read_value(file_path):
    with open(file_path, "r") as file:
        return file.read().strip()

# Function to get ADC0 voltage reading
def get_adc_voltage():
    scale_value = float(read_value(f"{ADC_DIR}/in_voltage_scale"))
    IN0_raw_value = float(read_value(f"{ADC_DIR}/in_voltage0_raw"))

    IN0_voltage = round(IN0_raw_value * scale_value / 1000, 3)
    return IN0_voltage

# Function to send ADC0 voltage data to Google Forms
def send_voltage():
    current_time = datetime.now().strftime("%I:%M:%S %p")  # Format time as HH:MM:SS AM/PM
    IN0_voltage = get_adc_voltage()  # Read ADC0 value

    data = {
        time_entry_id: current_time,
        voltage_entry_id: IN0_voltage,
    }

    response = requests.post(form_url, data=data)

    if response.status_code == 200:
        print(f"✔ Sent: Time={current_time}, IN0={IN0_voltage}V")
    else:
        print(f"❌ Error {response.status_code}: Failed to send data")

# Loop to send data every 30 seconds
while True:
    send_voltage()
    time.sleep(30)  # Wait 30 seconds before sending the next value
