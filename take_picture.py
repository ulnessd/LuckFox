import subprocess
import os
import sys
import shlex # Used for safer command construction if needed, though direct list is fine here

# --- Configuration ---
# Path to fswebcam executable (usually just the name if it's in PATH)
FSWEBCAM_CMD = "fswebcam"
# Default camera device (verify this on your LuckFox, e.g., /dev/video0, /dev/video1)
CAMERA_DEVICE = "/dev/video0"
# Default image resolution (adjust as needed)
RESOLUTION = "1280x720"
# Default save directory ('.' means current directory)
SAVE_DIRECTORY = "."
# --- End Configuration ---

def capture_image(filename):
    """Captures an image using fswebcam with the specified filename."""

    # Ensure the save directory exists
    try:
        os.makedirs(SAVE_DIRECTORY, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create directory '{SAVE_DIRECTORY}': {e}")
        return False

    # Construct the full path for the image file
    filepath = os.path.join(SAVE_DIRECTORY, filename)

    # Construct the fswebcam command as a list of arguments
    command = [
        FSWEBCAM_CMD,
        "-d", CAMERA_DEVICE,
        "-r", RESOLUTION,
        "--no-banner",  # Removes the default timestamp banner
        # Add other fswebcam options here if desired (e.g., -S for skip frames)
        filepath        # The final argument is the output file path
    ]

    print(f"\nAttempting to capture image using command:")
    # Use shlex.join for displaying command safely if needed, but printing list is ok
    print(f"  {' '.join(command)}")

    try:
        # Execute the command
        # capture_output=True suppresses fswebcam's normal output to console
        # text=True decodes stdout/stderr as text
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # check=True will raise CalledProcessError if fswebcam returns non-zero exit code

        print(f"\nSuccess! Image saved as: {filepath}")
        # print("fswebcam output (if any):") # Optional: print fswebcam stdout/stderr
        # print(result.stdout)
        # print(result.stderr, file=sys.stderr)
        return True

    except FileNotFoundError:
        print(f"\nError: '{FSWEBCAM_CMD}' command not found.")
        print("Please ensure fswebcam is installed (e.g., 'sudo apt-get install fswebcam')")
        return False
    except subprocess.CalledProcessError as e:
        print(f"\nError: fswebcam failed with exit code {e.returncode}.")
        print("fswebcam stdout:")
        print(e.stdout)
        print("fswebcam stderr:")
        print(e.stderr, file=sys.stderr)
        print(f"Failed command: {' '.join(command)}")
        return False
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return False

# --- Main Program ---
if __name__ == "__main__":
    print("--- USB Camera Image Capture ---")

    # Prompt user for filename
    try:
        filename_input = input("Enter a filename for the image (e.g., photo1.jpg): ").strip()

        # Basic validation
        if not filename_input:
            print("Error: No filename provided. Exiting.")
            sys.exit(1)

        # Ensure filename ends with .jpg (or other desired format)
        if not filename_input.lower().endswith(('.jpg', '.jpeg', '.png')):
             # Add .jpg if no common image extension is found
             print(f"Adding default extension '.jpg' to filename.")
             filename_input += ".jpg"

        # Optional: Add more robust filename sanitization here if needed
        # to prevent path traversal ('../') or invalid characters.
        # For basic use, this is often sufficient.

    except EOFError: # Handle Ctrl+D
        print("\nInput cancelled. Exiting.")
        sys.exit(0)
    except KeyboardInterrupt: # Handle Ctrl+C
        print("\nOperation cancelled by user. Exiting.")
        sys.exit(0)


    # Call the capture function
    capture_image(filename_input)
