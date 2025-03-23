from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont
import time


# Initialize OLED display
serial = i2c(port=3, address=0x3C)
device = ssd1306(serial)

# Load a TrueType font with a larger size
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Change if needed
font = ImageFont.truetype(font_path, 20)  # Adjust font size here (e.g., 20)

# Display text with the custom font
with canvas(device) as draw:
    draw.text((1, 2), "Hello", font=font, fill="white")
    draw.text((1, 22), "From the", font=font, fill="white")

    draw.text((1, 42), "GNL Project!", font=font, fill="white")

time.sleep(6)
