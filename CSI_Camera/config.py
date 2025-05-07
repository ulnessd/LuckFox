# ~/projects/camera/config.py

# --- Serial Communication Configuration ---
SERIAL_PORT = "/dev/ttyS3"  # Serial port on LuckFox A
BAUD_RATE = 115200
SERIAL_READ_TIMEOUT_S = 0.1  # Timeout for ser.read()
SERIAL_COMMAND_TIMEOUT_S = 10.0 # Default timeout for expecting a prompt after a command
SERIAL_LOGIN_TIMEOUT_S = 15.0 # Timeout for login sequence prompts

# --- Target Reboot Configuration ---
REBOOT_WAIT_SECONDS = 30 # <<< ADD THIS LINE (Adjust value as needed)

# --- Target (LuckFox B) Credentials & Prompts ---
TARGET_USERNAME = "root"
TARGET_PASSWORD = "luckfox" # Ensure this is secure if used in a production environment

# Prompts (ensure these exactly match what your target outputs)
# Using strings here, will be encoded to bytes in serial_ops
LOGIN_PROMPT_STR = "login: "
PASSWORD_PROMPT_STR = "Password: "
# Common shell prompts. The script will try to match any of these.
SHELL_PROMPT_STRS = ["[root@luckfox ~]# ", "[root@luckfox root]# ", "# "]

# --- Target Camera & Image Configuration ---
CSI_CAMERA_DEVICE_NODE = "/dev/video15"
CAPTURE_RESOLUTION_WIDTH = "240"
CAPTURE_RESOLUTION_HEIGHT = "135"
CAPTURE_PIXELFORMAT = "NV12"  # Raw YUV format (used by v4l2-ctl and ffmpeg)
TARGET_IMAGE_PATH = "/tmp/csi_capture.yuv"  # Where raw image is saved on LuckFox B

# --- Services on Target to Manage ---
SERVICES_TO_STOP = ["rkipc"] # Services to kill before camera operations

# --- File Transfer & Local Conversion Configuration ---
# In config.py (Example modification)
LOCAL_IMAGE_OUTPUT_DIRECTORY = "./captured_images" # Base directory
# Optional: filename prefixes or templates if you want a consistent start
RAW_IMAGE_PREFIX = "capture_raw_"
JPG_IMAGE_PREFIX = "capture_final_"

SCP_TIMEOUT_S = 60 # Timeout for the scp command
FFMPEG_TIMEOUT_S = 30 # Timeout for the ffmpeg command

# --- Session Reporting ---
SESSION_REPORT_FILE = "luckfox_session_report.log"

# --- IP Configuration ---
TARGET_NETWORK_INTERFACE = "eth0" # Network interface on LuckFox B to get IP from
