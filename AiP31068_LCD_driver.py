# -*- coding: utf-8 -*-
# CPython driver for Waveshare LCD1602 I2C Module (AiP31068L Controller)
# Ported from Waveshare's MicroPython example logic
# Assumes direct control via AiP31068L at address 0x3E (0x7c >> 1)

import smbus2 as smbus # Use smbus2
import time

class AiP31068_LCD_driver:
    # Define LCD device constants from MicroPython code
    LCD_WIDTH = 16   # Maximum characters per line
    LCD_CHR = 0x40   # Control byte for sending data
    LCD_CMD = 0x80   # Control byte for sending command

    # Commands (HD44780 compatible based on MicroPython code)
    LCD_CLEARDISPLAY = 0x01
    LCD_RETURNHOME = 0x02
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_CURSORSHIFT = 0x10
    LCD_FUNCTIONSET = 0x20
    LCD_SETCGRAMADDR = 0x40
    LCD_SETDDRAMADDR = 0x80

    # Flags for entry mode
    LCD_ENTRYRIGHT = 0x00
    LCD_ENTRYLEFT = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00

    # Flags for display on/off control
    LCD_DISPLAYON = 0x04
    LCD_DISPLAYOFF = 0x00
    LCD_CURSORON = 0x02
    LCD_CURSOROFF = 0x00
    LCD_BLINKON = 0x01
    LCD_BLINKOFF = 0x00

    # Flags for function set
    # Note: MicroPython code seems to default to 4-bit mode implicitly for AiP31068L
    # LCD_8BITMODE = 0x10
    # LCD_4BITMODE = 0x00 # Assumed
    LCD_2LINE = 0x08
    LCD_1LINE = 0x00
    LCD_5x8DOTS = 0x00

    # Line addresses
    LCD_LINE_1 = 0x80
    LCD_LINE_2 = 0xC0
    LCD_LINE_3 = 0x94 # For larger displays
    LCD_LINE_4 = 0xD4 # For larger displays

    def __init__(self, addr, port, cols=16, rows=2):
        self.addr = addr
        self.port = port
        self.cols = cols
        self.rows = rows
        self.bus = smbus.SMBus(self.port)

        # Initialize display based on MicroPython begin() logic
        self._showfunction = self.LCD_1LINE | self.LCD_5x8DOTS # Base function set
        if self.rows > 1:
            self._showfunction |= self.LCD_2LINE

        # Initialization sequence (matches MicroPython example)
        time.sleep(0.05) # Wait for >40 ms after power on

        # Send function set command sequence multiple times
        # AiP31068L seems to require this, similar to HD44780 init
        self._write_command(self.LCD_FUNCTIONSET | self._showfunction)
        time.sleep(0.005) # wait more than 4.1ms
        self._write_command(self.LCD_FUNCTIONSET | self._showfunction)
        time.sleep(0.001) # wait more than 100us
        self._write_command(self.LCD_FUNCTIONSET | self._showfunction)
        # MicroPython code sends it a 4th time, let's replicate
        self._write_command(self.LCD_FUNCTIONSET | self._showfunction)

        # Turn display on with no cursor or blinking default
        self._showcontrol = self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF
        self._write_command(self.LCD_DISPLAYCONTROL | self._showcontrol)

        # Clear display
        self.clear()

        # Set default entry mode (left to right)
        self._showmode = self.LCD_ENTRYLEFT | self.LCD_ENTRYSHIFTDECREMENT
        self._write_command(self.LCD_ENTRYMODESET | self._showmode)

        # --- Backlight Note ---
        # This driver does NOT explicitly control backlight via specific methods
        # It relies on the AiP31068L defaulting to ON, or potentially being
        # controlled by external means or specific vendor commands not included here.
        # Based on smbus2 tests, sending command 0x08 might turn it on, 0x00 off.

    # --- Low-level write functions ---
    def _write_command(self, cmd):
        """Sends a command byte using the command control byte."""
        try:
            self.bus.write_byte_data(self.addr, self.LCD_CMD, cmd)
            time.sleep(0.001) # Short delay after command
        except OSError as e:
            print(f"I2C Error writing command {hex(cmd)} to {hex(self.addr)}: {e}")

    def _write_data(self, data):
        """Sends a data byte using the data control byte."""
        try:
            self.bus.write_byte_data(self.addr, self.LCD_CHR, data)
            time.sleep(0.001) # Short delay after data
        except OSError as e:
            print(f"I2C Error writing data {hex(data)} to {hex(self.addr)}: {e}")

    # --- User-level methods ---
    def clear(self):
        """Clear display and return cursor to home."""
        self._write_command(self.LCD_CLEARDISPLAY)
        time.sleep(0.005) # Clear command needs extra delay

    def setCursor(self, col, row):
        """Set cursor position (col, row) - 0 based."""
        if row >= self.rows or row < 0 or col >= self.cols or col < 0:
             raise IndexError("Cursor position out of range")
        row_offsets = [self.LCD_LINE_1, self.LCD_LINE_2, self.LCD_LINE_3, self.LCD_LINE_4]
        addr = row_offsets[row] + col
        self._write_command(addr)

    def printout(self, message):
        """Prints string at current cursor position."""
        if isinstance(message, int):
            message = str(message)
        elif not isinstance(message, str):
            message = str(message) # Convert other types to string

        for char in message:
            self._write_data(ord(char))

    def display_string(self, message, line):
         """Write string to specified line (1 or 2)."""
         if line == 1:
             self.setCursor(0, 0)
         elif line == 2:
             self.setCursor(0, 1)
         # Add more lines if needed
         else:
             self.setCursor(0, 0) # Default to line 1

         # Truncate or pad message (optional)
         # message = message.ljust(self.cols," ")[:self.cols]
         self.printout(message)

    # --- Backlight Control (Experimental based on smbus2 tests) ---
    def backlight_on(self):
        """Turns backlight ON (experimental)."""
        print("Attempting Backlight ON (Cmd 0x08)...")
        # This assumes 0x08 sent as a command controls backlight
        # This might interfere with other display states if 0x08 is a real command!
        # Use with caution or investigate AiP31068L datasheet for proper control.
        self._write_command(0x08) # Revisit this based on datasheet / further tests

    def backlight_off(self):
        """Turns backlight OFF (experimental)."""
        print("Attempting Backlight OFF (Cmd 0x00)...")
        # This assumes 0x00 sent as a command controls backlight (and maybe resets?)
        # Use with caution. Sending 0x00 might be NOP or problematic.
        # A safer way might require knowing the exact display control register.
        self._write_command(0x00) # Revisit this

    # Cleanup
    def close(self):
        """Close the I2C bus."""
        if self.bus:
            self.bus.close()
            self.bus = None

    def __del__(self):
        # Destructor to close bus
        self.close()
