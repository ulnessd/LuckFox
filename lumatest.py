from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import time


serial = i2c(port=3, address=0x3C)  # Use correct I2C port
device = ssd1306(serial)

# Create blank image
image = Image.new("1", (device.width, device.height), "black")
draw = ImageDraw.Draw(image)

# Draw some text
font = ImageFont.load_default()
draw.text((4, 2), "Hello", font=font, fill="white")
draw.text((4,12), "from the", font=font, fill="white")
draw.text((4,22), "GNL Project!", font=font, fill="white")

# Display on OLED
device.display(image)

time.sleep(6)
