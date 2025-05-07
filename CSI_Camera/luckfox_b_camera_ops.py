# ~/projects/camera/luckfox_b_camera_ops.py

import time
import re
from datetime import datetime
# Assuming luckfox_b_serial_ops.py is in the same directory or PYTHONPATH
import luckfox_b_serial_ops as ser_ops

def _log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [CameraOps] {message}")


def manage_target_services(ser, shell_prompt_strs, services, action="stop", cmd_timeout_s=5.0):
    """Stops or starts services on the target. 'action' can be 'stop' or 'start'."""
    if action == "stop":
        command_template = "killall {service} || true" # || true to prevent error if not running
    elif action == "start": # Placeholder, actual start command might vary
        command_template = "{service} &" # Example, highly dependent on service
    else:
        _log(f"Unsupported service action: {action}", level="ERROR")
        return False

    all_successful = True
    for service_name in services:
        command = command_template.format(service=service_name)
        _log(f"Attempting to {action} service '{service_name}' on target with command: {command}")
        output = ser_ops.send_command_and_get_output(ser, command, shell_prompt_strs,
                                                     prompt_timeout_after_cmd_s=cmd_timeout_s,
                                                     suppress_debug_log=True)
        if output is None: # Command timed out or failed to return prompt
            _log(f"No clear response after trying to {action} service '{service_name}'. May have failed.", level="WARNING")
            all_successful = False # Mark as potentially failed
        else:
            _log(f"Service '{service_name}' {action} command sent. Output (if any): {output.strip()}", level="DEBUG")
        time.sleep(0.2) # Small delay between service commands
    return all_successful


def configure_and_capture_image(ser, device_node, cap_width, cap_height, cap_format,
                                target_image_path, shell_prompt_strs, cmd_timeout_s=15.0):
    """Configures the camera and captures an image using v4l2-ctl."""
    _log(f"Configuring camera {device_node} and capturing to {target_image_path}...")
    v4l2_command = (
        f"v4l2-ctl --device={device_node} "
        f"--set-fmt-video=width={cap_width},height={cap_height},pixelformat={cap_format} "
        f"--stream-mmap --stream-count=1 --stream-to={target_image_path}"
    )
    _log(f"Sending v4l2-ctl command: {v4l2_command}", level="DEBUG")
    output = ser_ops.send_command_and_get_output(ser, v4l2_command, shell_prompt_strs,
                                                 prompt_timeout_after_cmd_s=cmd_timeout_s,
                                                 suppress_debug_log=True)

    if output is None:
        _log("No response after v4l2-ctl capture command. Capture likely failed.", level="ERROR")
        return False

    # v4l2-ctl can be verbose; its output isn't always an error.
    # The main success indicator is if the prompt returns and the file is created.
    _log(f"v4l2-ctl command output (if any):\n{output.strip()}", level="DEBUG")
    _log("v4l2-ctl capture command sent. Verification of file needed.")
    time.sleep(0.5) # Give a moment for file system to sync after capture
    return True


def verify_capture_on_target(ser, target_image_path, shell_prompt_strs, cmd_timeout_s=5.0):
    """
    Verifies image creation on the target and returns its size.
    Returns file size (int > 0) on success, 0 on failure or if file not found/empty.
    """
    _log(f"Verifying image file '{target_image_path}' on target...")
    # Use --color=never to avoid ANSI escape codes in ls output.
    ls_command = f"ls -l --color=never {target_image_path}"
    raw_ls_output = ser_ops.send_command_and_get_output(ser, ls_command, shell_prompt_strs,
                                                        prompt_timeout_after_cmd_s=cmd_timeout_s,
                                                        suppress_debug_log=True)

    if raw_ls_output is None:
        _log("Failed to get 'ls -l' output from target.", level="ERROR")
        return 0

    _log(f"Raw 'ls -l' output: '{raw_ls_output}'", level="DEBUG")

    # Clean potential ANSI codes again, just in case --color=never wasn't effective or supported minimally
    ansi_escape_pattern = re.compile(r'\x1b\[[0-9;]*m')
    cleaned_ls_output = ansi_escape_pattern.sub('', raw_ls_output)
    _log(f"Cleaned 'ls -l' output: '{cleaned_ls_output}'", level="DEBUG")


    if "No such file or directory" in cleaned_ls_output or "cannot access" in cleaned_ls_output:
        _log(f"File '{target_image_path}' not found on target or error accessing.", level="ERROR")
        return 0
    if not cleaned_ls_output.strip(): # Empty output after cleaning
        _log(f"'ls -l' output was empty after cleaning for '{target_image_path}'. File likely does not exist.", level="ERROR")
        return 0

    parts = cleaned_ls_output.split()
    _log(f"Parsed 'ls -l' parts: {parts}", level="DEBUG")

    # Expected format for `ls -l /path/to/file`:
    # -rw-r--r-- 1 root root 48480 May 7 10:00 /tmp/csi_capture.yuv
    # parts[4] is size, parts[-1] (or near end) is filename.
    if len(parts) >= 5:
        # Check if the target path is correctly identified in the output parts
        # This is crucial because `ls -l /path/to/file` should list just that file.
        if parts[-1] == target_image_path:
            try:
                file_size = int(parts[4])
                if file_size > 0:
                    _log(f"File '{target_image_path}' verified with size: {file_size} bytes.")
                    return file_size
                else:
                    _log(f"File '{target_image_path}' found but size is 0.", level="ERROR")
                    return 0
            except (ValueError, IndexError) as e:
                _log(f"Error parsing size from 'ls -l' output. Parts: {parts}, Error: {e}", level="ERROR")
                return 0
        else:
            _log(f"Filename mismatch in 'ls -l' output. Expected '{target_image_path}', found last part '{parts[-1] if parts else 'N/A'}'.", level="ERROR")
            _log(f"Full 'ls -l' parts: {parts}", level="DEBUG")
            # Fallback: if target_image_path is ANY of the parts and it's a typical ls -l output line
            if target_image_path in parts and len(parts) > 8 : # e.g. permissions, links, owner, group, size, month, day, time, filename
                 try:
                    file_size = int(parts[4])
                    if file_size > 0:
                        _log(f"File '{target_image_path}' found in parts (not last) with size: {file_size} bytes.", level="WARNING")
                        return file_size
                 except (ValueError, IndexError):
                     pass # Failed to parse size even if filename was found somewhere.
            return 0
    else:
        _log(f"Unexpected 'ls -l' output format or too few parts ({len(parts)}). Cannot determine file size.", level="ERROR")
        return 0

def cleanup_target_image(ser, target_image_path, shell_prompt_strs, cmd_timeout_s=5.0):
    """Deletes the specified image file on the target."""
    _log(f"Deleting temporary file '{target_image_path}' on target...")
    rm_command = f"rm -f {target_image_path}"
    output = ser_ops.send_command_and_get_output(ser, rm_command, shell_prompt_strs,
                                                 prompt_timeout_after_cmd_s=cmd_timeout_s,
                                                 suppress_debug_log=True)
    if output is None:
        _log(f"No response after 'rm' command. Deletion status unknown for {target_image_path}.", level="WARNING")
        return False # Indicate uncertainty or failure
    _log(f"'rm -f {target_image_path}' command sent. Output (if any): {output.strip()}", level="DEBUG")
    return True
