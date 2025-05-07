# ~/projects/camera/luckfox_b_file_ops.py

import os
import subprocess
from datetime import datetime

def _log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [FileOps] {message}")

def transfer_image_scp(target_ip, target_user, remote_path, local_path, scp_timeout_s):
    """Transfers a file from target to local host using SCP."""
    _log(f"Initiating SCP transfer from root@{target_ip}:{remote_path} to {local_path}...")
    # Ensure local save directory exists
    local_dir = os.path.dirname(local_path)
    if local_dir and not os.path.exists(local_dir):
        try:
            os.makedirs(local_dir, exist_ok=True)
            _log(f"Created local directory: {local_dir}", level="DEBUG")
        except OSError as e:
            _log(f"Failed to create local directory {local_dir}: {e}", level="ERROR")
            return False

    scp_command = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10", # SCP's own connection timeout
        f"{target_user}@{target_ip}:{remote_path}",
        local_path
    ]
    _log(f"Executing SCP: {' '.join(scp_command)}", level="DEBUG")
    try:
        result = subprocess.run(scp_command, capture_output=True, text=True, timeout=scp_timeout_s)
        if result.returncode == 0:
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                _log(f"SCP successful. Raw image saved to {local_path}, size: {os.path.getsize(local_path)} bytes.")
                return True
            else:
                _log(f"SCP command returned success, but file {local_path} is missing or empty.", level="ERROR")
                _log(f"SCP stdout: {result.stdout.strip()}", level="DEBUG")
                _log(f"SCP stderr: {result.stderr.strip()}", level="DEBUG")
                return False
        else:
            _log(f"SCP failed with return code {result.returncode}.", level="ERROR")
            _log(f"SCP stdout: {result.stdout.strip()}", level="DEBUG")
            _log(f"SCP stderr: {result.stderr.strip()}", level="DEBUG")
            return False
    except subprocess.TimeoutExpired:
        _log("SCP command timed out.", level="ERROR")
        return False
    except Exception as e:
        _log(f"An unexpected error occurred during SCP: {e}", level="ERROR")
        return False

def process_local_image_ffmpeg(raw_image_path, jpg_image_path,
                               cap_width, cap_height, cap_format,
                               actual_file_size, # Pass the size obtained from target or after SCP
                               ffmpeg_timeout_s):
    """Pads the raw image if necessary and converts YUV to JPG using FFmpeg."""
    _log(f"Processing local image {raw_image_path} to {jpg_image_path}...")

    if not os.path.exists(raw_image_path) or actual_file_size == 0:
        _log(f"Raw image file {raw_image_path} does not exist or is empty. Cannot process.", level="ERROR")
        return False

    try:
        cap_width_int = int(cap_width)
        cap_height_int = int(cap_height)

        # Calculate FFmpeg's expected size for NV12
        # Y plane: width * height
        # UV plane: width * (height / 2) (interleaved U and V components)
        # Note: For NV12, UV plane height for ffmpeg is often ceil(height/2.0) if height is odd.
        y_plane_size = cap_width_int * cap_height_int
        uv_plane_effective_height = (cap_height_int + 1) // 2 # Ceiling division for UV plane height
        uv_plane_size = cap_width_int * uv_plane_effective_height # NV12 UV plane width is full width
        ffmpeg_expected_size = y_plane_size + uv_plane_size

        _log(f"Actual raw file size: {actual_file_size}, FFmpeg calculated expected size for {cap_width}x{cap_height} {cap_format}: {ffmpeg_expected_size}", level="DEBUG")

        if actual_file_size < ffmpeg_expected_size:
            padding_needed = ffmpeg_expected_size - actual_file_size
            _log(f"Padding file {raw_image_path} with {padding_needed} zero bytes.", level="INFO")
            with open(raw_image_path, "ab") as f: # Append bytes in binary mode
                f.write(b'\0' * padding_needed)
        elif actual_file_size > ffmpeg_expected_size:
            _log(f"Warning: Actual file size {actual_file_size} is LARGER than FFmpeg's expected {ffmpeg_expected_size}. "
                 "Proceeding, but this could indicate an issue with format or capture.", level="WARNING")
        # If actual_size == ffmpeg_expected_size, no padding needed.

        ffmpeg_command = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-pix_fmt", cap_format.lower(), # FFmpeg uses lowercase pix_fmt
            "-s", f"{cap_width_int}x{cap_height_int}",
            "-i", raw_image_path,
            "-frames:v", "1",
            "-q:v", "2", # JPEG quality (1-5 is good, 2 is often default high)
            jpg_image_path
        ]
        _log(f"Executing FFmpeg: {' '.join(ffmpeg_command)}", level="DEBUG")
        result = subprocess.run(ffmpeg_command, capture_output=True, text=True, timeout=ffmpeg_timeout_s)

        if result.returncode == 0:
            if os.path.exists(jpg_image_path) and os.path.getsize(jpg_image_path) > 0:
                _log(f"FFmpeg conversion successful. JPG saved to {jpg_image_path}")
                return True
            else:
                 _log(f"FFmpeg command successful, but output JPG {jpg_image_path} is missing or empty.", level="ERROR")
                 _log(f"FFmpeg stdout:\n{result.stdout.strip()}", level="DEBUG")
                 _log(f"FFmpeg stderr:\n{result.stderr.strip()}", level="DEBUG")
                 return False
        else:
            _log(f"FFmpeg conversion failed with return code {result.returncode}.", level="ERROR")
            _log(f"FFmpeg stdout:\n{result.stdout.strip()}", level="DEBUG")
            _log(f"FFmpeg stderr:\n{result.stderr.strip()}", level="DEBUG")
            return False
    except ValueError:
        _log("Error converting capture dimensions to integers for FFmpeg.", level="ERROR")
        return False
    except subprocess.TimeoutExpired:
        _log("FFmpeg command timed out.", level="ERROR")
        return False
    except Exception as e:
        _log(f"An unexpected error occurred during FFmpeg processing: {e}", level="ERROR")
        return False
