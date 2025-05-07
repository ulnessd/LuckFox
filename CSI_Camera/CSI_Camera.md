# LuckFox Pico Remote Camera Control via Serial/Network

## Introduction

This project demonstrates controlling a LuckFox Pico Pro/Max board (running the vendor's Buildroot OS) from a second LuckFox board (running Ubuntu) to capture single, on-demand images from a connected CSI camera.

The LuckFox Pico platform, with its Rockchip RV1106 SoC and integrated ISP, is well-suited for vision tasks. However, the default Buildroot system typically runs the `rkipc` service, providing a continuous video stream suitable for monitoring but difficult to adapt for single-shot captures. This project bypasses `rkipc` by using a serial UART connection for control (login, service management, `v4l2-ctl` execution) and SCP over the network for retrieving the captured raw image data. The raw image is then processed locally on the host into a standard JPEG file using FFmpeg, including necessary workarounds for driver-specific data formatting.

The primary motivation is to enable the use of the LuckFox camera in applications requiring discrete image capture, such as scientific instrumentation, data logging, or event-triggered monitoring, rather than continuous streaming.

**Key Limitation Overview:** Due to camera driver state issues encountered on the target Buildroot system (specifically involving the Rockchip ISP `rkisp` driver not resetting correctly after a `v4l2-ctl` raw capture), this solution currently requires a **mandatory reboot** of the target board before each capture. The final script automates this reboot via serial, making it a reliable **single-shot capture** system per execution cycle.

## Hardware Requirements

1.  **Host:** LuckFox Pico Max (or Pro) running Ubuntu (tested with 22.04 LTS on an SD card).
2.  **Target:** LuckFox Pico Max (or Pro) running the vendor-supplied Buildroot OS (installed on NAND Flash).
3.  **Camera:** MIPI CSI camera compatible with the LuckFox board (tested with SC3336 3MP module).
4.  **Serial Connection:**
    * USB-to-Serial adapter (if connecting Host UART3 to PC for debugging initially) OR direct connection between boards.
    * Jumper wires for connecting Host UART3 TX/RX/GND to Target UART2 RX/TX/GND.
5.  **Network Connection:** Ethernet cables and a network switch/router to connect both boards to the same LAN.
6.  **Power Supplies:** Appropriate power supplies for both boards.

## Software Requirements & Setup

### Host Setup (LuckFox A - Ubuntu)

1.  **OS:** Ubuntu 22.04 LTS recommended.
2.  **Python:** Python 3 (usually pre-installed on Ubuntu).
3.  **Required Python Packages:**
    ```bash
    pip install pyserial
    # or: sudo apt update && sudo apt install python3-serial
    ```
4.  **Required Linux Packages:**
    ```bash
    sudo apt update
    sudo apt install ffmpeg openssh-client
    ```
    * `ffmpeg`: For converting the captured raw YUV image to JPG.
    * `openssh-client`: Provides the `scp` command for file transfer.

### Target Setup (LuckFox B - Buildroot)

1.  **OS:** Vendor-supplied Buildroot image.
2.  **SSH Server:** An SSH server must be running and configured to allow root login for SCP to work. The default Buildroot image likely includes `dropbear` as the SSH server. Ensure it's enabled. Default credentials are typically `root` / `luckfox`.
3.  **Camera Connected:** Ensure the CSI camera is correctly connected *before* booting the Target board. (Note: For Pico Pro/Max, the metal contact side of the FPC cable usually faces the main chip).
4.  **`v4l2-utils`:** This package (containing `v4l2-ctl`) should be pre-installed on the vendor Buildroot image. No manual installation is typically needed.

### Connections

1.  **Serial:** Connect Host UART3 to Target UART2:
    * Host Pin 19 (TXD3) -> Target Pin 2 (RXD2)
    * Host Pin 20 (RXD3) -> Target Pin 1 (TXD2)
    * Host GND -> Target GND (Pin 3 or another GND pin)
2.  **Network:** Connect both boards via Ethernet cables to your LAN switch or router.

## Project File Structure

~/projects/camera/
├── luckfox_image_capture.py  # Main application script (handles reboot, wait, capture)
├── config.py                 # Configuration settings (ports, credentials, paths, etc.)
├── luckfox_b_serial_ops.py   # Module for serial port operations & login
├── luckfox_b_camera_ops.py   # Module for camera/v4l2 commands on target
├── luckfox_b_file_ops.py     # Module for SCP transfer and FFmpeg processing
│
├── captured_images/          # Default directory for output images (created automatically)
│   └── capture_final_.jpg   # Example output JPG
│   └── capture_raw_.yuv     # Example output raw YUV (padded)
│
└── luckfox_session_report.log # Log file for script execution details

## Configuration (`config.py`)

Before running the script, **carefully review and edit `config.py`**. Key settings include:

* `SERIAL_PORT`: Serial port on the Host (e.g., `/dev/ttyS3`).
* `TARGET_USERNAME`, `TARGET_PASSWORD`: Credentials for the Target Buildroot system. **Note:** Storing passwords in plain text is insecure; consider alternatives like SSH keys if deploying widely.
* `LOGIN_PROMPT_STR`, `PASSWORD_PROMPT_STR`, `SHELL_PROMPT_STRS`: Ensure these match the exact prompts on your Target's serial console.
* `CSI_CAMERA_DEVICE_NODE`: V4L2 device node for the camera on Target (e.g., `/dev/video15`).
* `CAPTURE_RESOLUTION_WIDTH`, `CAPTURE_RESOLUTION_HEIGHT`, `CAPTURE_PIXELFORMAT`: Parameters for `v4l2-ctl`.
* `TARGET_IMAGE_PATH`: Temporary path to save the raw image *on the Target*.
* `LOCAL_IMAGE_OUTPUT_DIRECTORY`, `RAW_IMAGE_PREFIX`, `JPG_IMAGE_PREFIX`: Define where processed images are saved locally and how they are named.
* `REBOOT_WAIT_SECONDS`: **Crucial.** Set this to the number of seconds needed for the Target board to fully reboot and become responsive on the serial console after the `reboot` command is sent (e.g., `75`). Adjust based on testing.
* Other timeouts (`SERIAL_COMMAND_TIMEOUT_S`, `SCP_TIMEOUT_S`, etc.).

## Usage

1.  Ensure all hardware is connected and both boards are powered and connected to the network.
2.  Navigate to the project directory on the Host board: `cd ~/projects/camera`
3.  Run the main script:
    ```bash
    python3 luckfox_image_capture.py
    ```

**Execution Flow:**

1.  The script connects to the Target via serial (`config.SERIAL_PORT`).
2.  It logs in using the configured credentials.
3.  It sends the `reboot` command to the Target.
4.  It disconnects the initial serial connection.
5.  It waits for `config.REBOOT_WAIT_SECONDS`.
6.  After the wait, it attempts to reconnect via serial.
7.  It logs in again.
8.  It sends `killall rkipc` to stop the default camera service (in case it auto-restarted).
9.  It gets the Target's IP address using `ip addr show eth0` (or fallback).
10. It sends the `v4l2-ctl` command to capture a single raw frame to `config.TARGET_IMAGE_PATH`.
11. It verifies the capture using `ls -l` on the Target.
12. It transfers the raw image file from Target to Host using `scp` into the `config.LOCAL_IMAGE_OUTPUT_DIRECTORY` with a unique filename.
13. It pads the local raw file (if needed) to match FFmpeg's expectations for NV12 with odd heights.
14. It converts the padded raw YUV file to a JPG image using `ffmpeg`.
15. It cleans up the raw image file on the Target using `rm`.
16. It logs out and closes the serial connection.
17. Progress and results are printed to the console and logged to `luckfox_session_report.log`.

## Key Challenges and Limitations

* **`rkipc` Console Spew:** The default Buildroot system floods the serial console with `rkipc` logs, making manual login impossible and requiring careful automation to log in and kill the service.
* **NV12 Padding:** The specific NV12 implementation for 240x135 resolution resulted in a file size (48480 bytes) inconsistent with FFmpeg's expectation (48720 bytes) due to how odd heights are handled in YUV 4:2:0 chroma planes. The script automatically pads the local raw file with null bytes before conversion.
* **Sequential Capture Failure / Mandatory Reboot:** The most significant limitation is that the camera subsystem (specifically the `rkisp` driver) on the target Buildroot board enters an unusable state after a single raw capture via `v4l2-ctl`. Subsequent capture attempts fail with `VIDIOC_STREAMON returned -1 (Invalid argument)` errors, related to `rkisp-vir0` failing to start and `entity use_count` being incorrect. Attempts to reset this state by reloading kernel modules failed due to the inability to unload `video_rkisp` ("Resource temporarily unavailable") and a non-functional `modprobe` utility on the target.
* **Single-Shot Workaround:** Consequently, the only reliable way found to perform captures was to reboot the target board before each capture. The final script automates this reboot trigger, making it a functional but inherently single-shot-per-cycle system.

## Future Considerations

* Investigate fixing `modprobe` and module unloading on the Target Buildroot system to enable software-based driver resets.
* Explore alternative capture libraries/methods (GStreamer, direct V4L2 C code) on the Target that might manage driver state more gracefully.
* Consult LuckFox/Rockchip communities for patches or known workarounds for the `rkisp` state issue with `v4l2-ctl`.
* Implement SSH key-based authentication for passwordless SCP.
* Explore hardware reset mechanisms (Reset Pin, GPIO power control) if the software reboot proves unreliable long-term.

## License

(Consider adding an open-source license here, e.g., MIT, Apache 2.0)

## Acknowledgements

* Project by Darin J. Ulness (GNL Project).
* Assistance provided by Google Gemini.
* LuckFox documentation.

