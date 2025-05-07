# ~/projects/camera/luckfox_image_capture.py

import time
from datetime import datetime
import os
import sys

# Import your modules
import config as cfg
import luckfox_b_serial_ops as ser_ops
import luckfox_b_camera_ops as cam_ops
import luckfox_b_file_ops as file_ops

# --- Session Report Helper ---
# (Using the same logging setup as before)
session_log_entries = []

def log_to_controller_and_session(message, level="INFO"):
    global session_log_entries
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color_start = ""
    color_end = "\033[0m" # Reset color
    if level == "ERROR": color_start = "\033[91m"
    elif level == "WARNING": color_start = "\033[93m"
    elif level == "IMPORTANT": color_start = "\033[94m"
    elif level == "SUCCESS": color_start = "\033[92m"

    console_msg = f"{color_start}[{timestamp}] [{level}] [CaptureFlow] {message}{color_end}" # Changed tag
    print(console_msg)
    session_log_entries.append(f"[{timestamp}] [{level}] [CaptureFlow] {message}")

def write_session_report_file():
    global session_log_entries
    if not session_log_entries: return
    try:
        report_dir = os.path.dirname(cfg.SESSION_REPORT_FILE)
        if report_dir and not os.path.exists(report_dir): os.makedirs(report_dir, exist_ok=True)
        with open(cfg.SESSION_REPORT_FILE, "a") as f:
            f.write(f"\n--- New Session Started: {session_log_entries[0].split('] [CaptureFlow] ')[0].split(' ')[0]}] ---\n")
            for entry in session_log_entries: f.write(entry + "\n")
            f.write(f"--- Session Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        print(f"\033[92m[INFO] Session report appended to {cfg.SESSION_REPORT_FILE}\033[0m")
    except Exception as e:
        print(f"\033[91m[ERROR] Error writing session report: {e}\033[0m")

# --- Reboot Function ---
def trigger_target_reboot():
    """Connects via serial, logs in, sends reboot command, disconnects."""
    log_to_controller_and_session("Attempting to trigger reboot on target...", level="INFO")
    ser_reboot = None
    try:
        ser_reboot = ser_ops.connect_serial(cfg.SERIAL_PORT, cfg.BAUD_RATE, cfg.SERIAL_READ_TIMEOUT_S)
        if not ser_reboot:
            log_to_controller_and_session("Serial connection failed for reboot trigger.", level="ERROR")
            return False

        if not ser_ops.login_to_target(ser_reboot, cfg.TARGET_USERNAME, cfg.TARGET_PASSWORD,
                                       cfg.LOGIN_PROMPT_STR, cfg.PASSWORD_PROMPT_STR, cfg.SHELL_PROMPT_STRS,
                                       cfg.SERIAL_LOGIN_TIMEOUT_S):
            log_to_controller_and_session("Login failed for reboot trigger.", level="ERROR")
            # Consider if you still want to try sending reboot if login fails (e.g., already at prompt)
            # For now, we require login.
            return False

        log_to_controller_and_session("Sending 'reboot' command to target...", level="INFO")
        ser_reboot.write(b'reboot\n')
        ser_reboot.flush()
        time.sleep(0.5) # Give command a moment to register before closing
        log_to_controller_and_session("Reboot command sent.", level="SUCCESS")
        return True

    except Exception as e:
        log_to_controller_and_session(f"Exception during reboot trigger: {e}", level="ERROR")
        return False
    finally:
        if ser_reboot:
            ser_ops.close_serial(ser_reboot)

# --- Capture Sequence Function ---
# This is essentially the run_single_capture function from the previous version
def run_capture_sequence_after_reboot():
    """Runs the full capture sequence, assuming target has rebooted."""
    log_to_controller_and_session("Starting post-reboot capture sequence...", level="INFO")
    ser_capture = None
    overall_success = False

    # Generate unique filenames for this capture
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    current_local_raw_path = os.path.join(cfg.LOCAL_IMAGE_OUTPUT_DIRECTORY, f"{cfg.RAW_IMAGE_PREFIX}{timestamp_str}.yuv")
    current_local_jpg_path = os.path.join(cfg.LOCAL_IMAGE_OUTPUT_DIRECTORY, f"{cfg.JPG_IMAGE_PREFIX}{timestamp_str}.jpg")
    log_to_controller_and_session(f"Target local raw path: {current_local_raw_path}")
    log_to_controller_and_session(f"Target local JPG path: {current_local_jpg_path}")

    try:
        # 1. Connect Serial (post-reboot)
        log_to_controller_and_session("Attempting serial connection post-reboot...")
        ser_capture = ser_ops.connect_serial(cfg.SERIAL_PORT, cfg.BAUD_RATE, cfg.SERIAL_READ_TIMEOUT_S)
        if not ser_capture:
            log_to_controller_and_session("Fatal: Could not establish serial connection post-reboot.", level="ERROR")
            return False # Cannot proceed if connection fails

        # 2. Login to Target (post-reboot)
        log_to_controller_and_session("Attempting login post-reboot...")
        if not ser_ops.login_to_target(ser_capture, cfg.TARGET_USERNAME, cfg.TARGET_PASSWORD,
                                       cfg.LOGIN_PROMPT_STR, cfg.PASSWORD_PROMPT_STR, cfg.SHELL_PROMPT_STRS,
                                       cfg.SERIAL_LOGIN_TIMEOUT_S):
            log_to_controller_and_session("Fatal: Login to target failed post-reboot.", level="ERROR")
            return False
        log_to_controller_and_session("Successfully logged into target post-reboot.")

        # 3. Manage Target Services (stop rkipc, which might have auto-restarted)
        log_to_controller_and_session(f"Attempting to stop services post-reboot: {cfg.SERVICES_TO_STOP}...")
        if not cam_ops.manage_target_services(ser_capture, cfg.SHELL_PROMPT_STRS, cfg.SERVICES_TO_STOP, action="stop",
                                              cmd_timeout_s=cfg.SERIAL_COMMAND_TIMEOUT_S):
            log_to_controller_and_session(f"Warning: Could not reliably stop services post-reboot: {cfg.SERVICES_TO_STOP}. Continuing...", level="WARNING")
        else:
            log_to_controller_and_session(f"Services {cfg.SERVICES_TO_STOP} stop command(s) sent post-reboot.")

        # 4. Get Target IP Address (post-reboot)
        log_to_controller_and_session("Retrieving target IP address post-reboot...")
        target_ip = ser_ops.get_target_ip(ser_capture, cfg.SHELL_PROMPT_STRS, cfg.TARGET_NETWORK_INTERFACE,
                                          cmd_timeout_s=cfg.SERIAL_COMMAND_TIMEOUT_S)
        if not target_ip:
            log_to_controller_and_session("Fatal: Could not retrieve target IP address post-reboot.", level="ERROR")
            return False
        log_to_controller_and_session(f"Target IP address post-reboot: {target_ip}")

        # 5. Configure Camera and Capture Image
        log_to_controller_and_session("Configuring camera and capturing image on target...")
        if not cam_ops.configure_and_capture_image(ser_capture, cfg.CSI_CAMERA_DEVICE_NODE,
                                                   cfg.CAPTURE_RESOLUTION_WIDTH, cfg.CAPTURE_RESOLUTION_HEIGHT,
                                                   cfg.CAPTURE_PIXELFORMAT, cfg.TARGET_IMAGE_PATH,
                                                   cfg.SHELL_PROMPT_STRS, cmd_timeout_s=15.0):
            log_to_controller_and_session("Error: Failed to configure or capture image on target.", level="ERROR")
            raise Exception("Capture command failed")

        # 6. Verify Capture on Target
        target_file_size = cam_ops.verify_capture_on_target(ser_capture, cfg.TARGET_IMAGE_PATH, cfg.SHELL_PROMPT_STRS,
                                                             cmd_timeout_s=cfg.SERIAL_COMMAND_TIMEOUT_S)
        if target_file_size <= 0:
            log_to_controller_and_session("Error: Image verification failed on target.", level="ERROR")
            raise Exception("Target image verification failed")
        log_to_controller_and_session(f"Image successfully verified on target. Size: {target_file_size} bytes.")

        # 7. Transfer Image via SCP
        log_to_controller_and_session("Transferring image via SCP...")
        if not file_ops.transfer_image_scp(target_ip, cfg.TARGET_USERNAME, cfg.TARGET_IMAGE_PATH,
                                           current_local_raw_path, cfg.SCP_TIMEOUT_S):
            log_to_controller_and_session("Error: SCP image transfer failed.", level="ERROR")
            raise Exception("SCP transfer failed")
        log_to_controller_and_session(f"Image successfully transferred via SCP to {current_local_raw_path}.")
        local_raw_size_after_scp = os.path.getsize(current_local_raw_path) if os.path.exists(current_local_raw_path) else 0

        # 8. Process Local Image
        log_to_controller_and_session("Processing local image (FFmpeg)...")
        if not file_ops.process_local_image_ffmpeg(current_local_raw_path, current_local_jpg_path,
                                                  cfg.CAPTURE_RESOLUTION_WIDTH, cfg.CAPTURE_RESOLUTION_HEIGHT,
                                                  cfg.CAPTURE_PIXELFORMAT, local_raw_size_after_scp,
                                                  cfg.FFMPEG_TIMEOUT_S):
            log_to_controller_and_session("Error: Local image processing (FFmpeg) failed.", level="ERROR")
            # overall_success remains False
        else:
            log_to_controller_and_session(f"Local image successfully processed. Final JPG: {current_local_jpg_path}", level="SUCCESS")
            overall_success = True # Set success only if everything worked

    except Exception as e_capture:
        log_to_controller_and_session(f"An error occurred during the capture sequence: {e_capture}", level="ERROR")
        overall_success = False
    finally:
        # Cleanup and Disconnect for the capture phase
        if ser_capture:
            log_to_controller_and_session("Cleaning up target and disconnecting from capture session...", level="INFO")
            cam_ops.cleanup_target_image(ser_capture, cfg.TARGET_IMAGE_PATH, cfg.SHELL_PROMPT_STRS)
            ser_ops.logout_from_target(ser_capture, cfg.SHELL_PROMPT_STRS, cfg.LOGIN_PROMPT_STR, cfg.SERIAL_COMMAND_TIMEOUT_S)
            ser_ops.close_serial(ser_capture)
        else:
             log_to_controller_and_session("Serial connection for capture phase was not established.", level="WARNING")

    return overall_success

# --- Main Execution Block ---
if __name__ == "__main__":
    log_to_controller_and_session("Automated Reboot and Capture process starting...", level="IMPORTANT")

    # Step 1: Trigger Reboot
    if not trigger_target_reboot():
        log_to_controller_and_session("Failed to send reboot command. Cannot proceed.", level="ERROR")
        write_session_report_file() # Write logs accumulated so far
        sys.exit(1)

    # Step 2: Wait for Reboot
    log_to_controller_and_session(f"Waiting {cfg.REBOOT_WAIT_SECONDS} seconds for target to reboot...", level="IMPORTANT")
    time.sleep(cfg.REBOOT_WAIT_SECONDS)
    log_to_controller_and_session("Wait complete. Attempting capture sequence...", level="IMPORTANT")

    # Step 3: Run Capture Sequence
    start_time = time.monotonic()
    capture_success = run_capture_sequence_after_reboot() # This function now handles connection, capture, etc.
    end_time = time.monotonic()

    # Final Status Reporting
    if capture_success:
        log_to_controller_and_session("Overall process finished successfully.", level="SUCCESS")
        print("\n>>> IMAGE CAPTURE SUCCEEDED <<<\n")
    else:
        log_to_controller_and_session("Overall process FAILED.", level="ERROR")
        print("\n>>> IMAGE CAPTURE FAILED <<<\n")

    log_to_controller_and_session(f"Capture sequence execution time: {end_time - start_time:.2f} seconds.", level="INFO")
    write_session_report_file() # Write logs for the capture sequence part
    sys.exit(0 if capture_success else 1)
