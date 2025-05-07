# Example: reboot_target.py
import luckfox_b_serial_ops as ser_ops
import config as cfg
import time
print("Connecting to target to initiate reboot...")
ser = ser_ops.connect_serial(cfg.SERIAL_PORT, cfg.BAUD_RATE, cfg.SERIAL_READ_TIMEOUT_S)
if ser:
    if ser_ops.login_to_target(ser, cfg.TARGET_USERNAME, cfg.TARGET_PASSWORD, cfg.LOGIN_PROMPT_STR, cfg.PASSWORD_PROMPT_STR, cfg.SHELL_PROMPT_STRS, cfg.SERIAL_LOGIN_TIMEOUT_S):
        print("Sending reboot command...")
        # Send 'reboot' and don't necessarily wait for a prompt, as connection will drop
        ser.write(b'reboot\n')
        ser.flush()
        print("Reboot command sent. Closing serial port.")
    else:
        print("Login failed, cannot send reboot.")
    ser_ops.close_serial(ser)
else:
    print("Serial connection failed.")
print("Allowing time for target to reboot...")
# You would typically run your main script after this script finishes + a delay
