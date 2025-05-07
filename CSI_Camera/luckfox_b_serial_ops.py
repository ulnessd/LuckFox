# ~/projects/camera/luckfox_b_serial_ops.py

import serial
import time
import re
from datetime import datetime

# Helper for logging within this module (can be replaced by a passed logger)
def _log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [SerialOps] {message}")

def connect_serial(port, baudrate, timeout):
    """Establishes a serial connection."""
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        _log(f"Serial port {port} opened successfully.")
        return ser
    except serial.SerialException as e:
        _log(f"Failed to open serial port {port}: {e}", level="ERROR")
        return None

def close_serial(ser):
    """Closes the serial connection."""
    if ser and ser.is_open:
        try:
            ser.close()
            _log(f"Serial port {ser.port} closed.")
        except Exception as e:
            _log(f"Error closing serial port {ser.port}: {e}", level="ERROR")

def expect_prompt(ser, prompts_to_expect_bytes, timeout_duration, initial_buffer=b""):
    """
    Waits for one of the specified byte prompts on the serial line.
    `prompts_to_expect_bytes` must be a list of byte strings.
    Returns the full buffer up to and including the prompt, or None on timeout/error.
    """
    if not isinstance(prompts_to_expect_bytes, list):
        prompts_to_expect_bytes = [prompts_to_expect_bytes]

    received_buffer = initial_buffer
    start_time = time.monotonic()

    # Check initial buffer first
    for prompt_bytes_item in prompts_to_expect_bytes:
        if prompt_bytes_item in received_buffer:
            return received_buffer # Prompt found in initial data

    while time.monotonic() - start_time < timeout_duration:
        if ser.in_waiting > 0:
            try:
                byte_chunk = ser.read(ser.in_waiting)
                if byte_chunk:
                    received_buffer += byte_chunk
                    # _log(f"DEBUG expect_prompt RX: {byte_chunk.decode(errors='replace')}", level="DEBUG") # Very verbose
                    for prompt_bytes_item in prompts_to_expect_bytes:
                        if prompt_bytes_item in received_buffer:
                            return received_buffer # Prompt found after reading
            except serial.SerialException as e:
                _log(f"Serial read error in expect_prompt: {e}", level="ERROR")
                return None # Error during read
        time.sleep(0.02) # Small sleep to avoid pegging CPU

    # _log(f"Timeout in expect_prompt. Buffer (last 100): '{received_buffer[-100:].decode(errors='replace')}'", level="DEBUG")
    # _log(f"Failed to find any of: {[p.decode(errors='replace') for p in prompts_to_expect_bytes]}", level="DEBUG")
    return None # Timeout

def send_command_and_get_output(ser, command_str, shell_prompt_strs,
                                command_echo_timeout_s=1.0,
                                prompt_timeout_after_cmd_s=10.0,
                                suppress_debug_log=False):
    """
    Sends a command, waits for it to echo (optional), then reads until a shell prompt.
    Returns the cleaned output (without command echo and prompt), or None on error/timeout.
    `shell_prompt_strs` is a list of strings.
    """
    if not command_str.endswith('\n'):
        command_str += '\n'
    command_bytes = command_str.encode()
    shell_prompt_bytes = [p.encode() for p in shell_prompt_strs]

    if not suppress_debug_log:
        _log(f"Sending command: {command_str.strip()}", level="DEBUG")

    ser.reset_input_buffer()
    ser.write(command_bytes)
    ser.flush()

    # 1. Wait for command echo (and discard it)
    # This part is tricky because echo might not always happen or might be mangled.
    # A simpler approach is to just read until prompt and then try to strip echo later if present.
    # For now, we'll rely on stripping common echo patterns.

    # 2. Read until one of the shell prompts is seen
    full_response_buffer = b""
    start_time = time.monotonic()
    prompt_found_details = {"found": False, "prompt_bytes": None, "index": -1}

    while time.monotonic() - start_time < prompt_timeout_after_cmd_s:
        if ser.in_waiting > 0:
            try:
                chunk = ser.read(ser.in_waiting)
                if chunk:
                    full_response_buffer += chunk
                    for p_bytes in shell_prompt_bytes:
                        if full_response_buffer.endswith(p_bytes):
                            prompt_found_details = {"found": True, "prompt_bytes": p_bytes, "index": len(full_response_buffer) - len(p_bytes)}
                            break
                    if prompt_found_details["found"]:
                        break
            except serial.SerialException as e:
                _log(f"Serial read error in send_command: {e}", level="ERROR")
                return None
        else: # Check again even if no new data, in case prompt was already received
            if not prompt_found_details["found"]:
                 for p_bytes in shell_prompt_bytes:
                    if full_response_buffer.endswith(p_bytes):
                        prompt_found_details = {"found": True, "prompt_bytes": p_bytes, "index": len(full_response_buffer) - len(p_bytes)}
                        break
                 if prompt_found_details["found"]:
                    break
            time.sleep(0.05)

    if not prompt_found_details["found"]:
        # Last chance: check if any prompt is *anywhere* (not just end)
        for p_bytes in shell_prompt_bytes:
            idx = full_response_buffer.rfind(p_bytes)
            if idx != -1:
                if not prompt_found_details["found"] or idx > prompt_found_details["index"]: #get the latest one
                    prompt_found_details = {"found": True, "prompt_bytes": p_bytes, "index": idx}
        if not prompt_found_details["found"]:
            _log(f"Timeout or no prompt found after command '{command_str.strip()}'.", level="WARNING")
            _log(f"Buffer (last 200): {full_response_buffer[-200:].decode(errors='replace')}", level="DEBUG")
            return None

    # Process the buffer:
    # 1. Remove the prompt itself
    output_before_prompt = full_response_buffer[:prompt_found_details["index"]]

    # 2. Attempt to remove command echo.
    # Assumes echo is the first line and matches the command sent.
    output_lines = output_before_prompt.splitlines(True)
    command_sent_stripped = command_bytes.strip()
    
    cleaned_output_bytes = output_before_prompt # Default if no echo found
    if output_lines:
        first_line_stripped = output_lines[0].strip()
        if first_line_stripped == command_sent_stripped:
            cleaned_output_bytes = b"".join(output_lines[1:])
            if not suppress_debug_log:
                _log(f"Command echo '{first_line_stripped.decode(errors='replace')}' removed.", level="DEBUG")
        # Handle cases where console adds CRs or escapes that make exact match hard
        elif command_sent_stripped in first_line_stripped: # More lenient check
             #This is riskier, as it might remove part of actual output if command is a substring
             #_log(f"DEBUG: Potential partial echo found: {first_line_stripped.decode(errors='replace')}", level="DEBUG")
             pass


    final_output_str = cleaned_output_bytes.decode(errors='replace').strip()
    if not suppress_debug_log:
        _log(f"Command output: >>>\n{final_output_str}\n<<<", level="DEBUG")
    return final_output_str


def login_to_target(ser, username, password, login_prompt_str, password_prompt_str, shell_prompt_strs, login_timeout_s):
    """Handles the login sequence."""
    _log("Attempting to login...")
    try:
        # Send a newline to potentially clear buffers and get a prompt
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.write(b"\n")
        ser.flush()
        time.sleep(0.5)

        # Read initial output, looking for login prompt or existing shell prompt
        initial_prompts_bytes = [login_prompt_str.encode()] + [p.encode() for p in shell_prompt_strs]
        initial_response = expect_prompt(ser, initial_prompts_bytes, login_timeout_s / 2) # Shorter timeout for initial

        if initial_response is None:
            _log("No initial login or shell prompt detected.", level="WARNING")
            # Try sending another newline, sometimes helps wake up the console
            ser.write(b"\n"); ser.flush(); time.sleep(0.2)
            initial_response = expect_prompt(ser, initial_prompts_bytes, login_timeout_s / 2)
            if initial_response is None:
                 _log("Still no initial login or shell prompt after retry.", level="ERROR")
                 return False


        # Check if already at a shell prompt
        for shell_p_str in shell_prompt_strs:
            if shell_p_str.encode() in initial_response:
                _log("Already logged in (shell prompt detected).")
                return True

        # If login prompt is found
        if login_prompt_str.encode() in initial_response:
            _log("Login prompt detected. Sending username.")
            ser.write((username + "\n").encode())
            ser.flush()

            password_response = expect_prompt(ser, [password_prompt_str.encode()], login_timeout_s)
            if password_response is None:
                _log("Password prompt not detected after sending username.", level="ERROR")
                return False
            _log("Password prompt detected. Sending password.")
            ser.write((password + "\n").encode())
            ser.flush()

            shell_response = expect_prompt(ser, [p.encode() for p in shell_prompt_strs], login_timeout_s)
            if shell_response is None:
                _log("Shell prompt not detected after sending password. Login failed.", level="ERROR")
                return False
            _log("Login successful (shell prompt detected).")
            return True
        else:
            _log("Unknown state: Neither login nor shell prompt clearly identified.", level="ERROR")
            _log(f"Buffer: {initial_response.decode(errors='replace') if initial_response else 'None'}", level="DEBUG")
            return False

    except Exception as e:
        _log(f"Exception during login: {e}", level="ERROR")
        return False

def logout_from_target(ser, shell_prompt_strs, login_prompt_str, cmd_timeout_s):
    """Sends 'exit' command to log out."""
    _log("Attempting to logout...")
    try:
        # The output after 'exit' can be unpredictable: back to login, or connection close, or just another shell prompt if exit fails
        # We primarily want to ensure the command is sent.
        send_command_and_get_output(ser, "exit", shell_prompt_strs + [login_prompt_str], # Expect either shell or back to login
                                    prompt_timeout_after_cmd_s=cmd_timeout_s,
                                    suppress_debug_log=True) # Output not too important
        _log("Logout 'exit' command sent.")
        return True
    except Exception as e:
        _log(f"Exception during logout: {e}", level="WARNING")
        return False


def parse_ip_address_from_output(output_str, interface_name):
    """Parses IP address for a specific interface from 'ip addr show' or 'ifconfig' output."""
    # Regex for 'ip addr show <interface>'
    # Example: inet 192.168.50.5/24 brd 192.168.50.255 scope global eth0
    ip_addr_pattern = re.compile(rf"inet\s+(\d{{1,3}}\.\d{{1,3}}\.\d{{1,3}}\.\d{{1,3}})/\d+\s+.*?\b{re.escape(interface_name)}\b")
    match = ip_addr_pattern.search(output_str)
    if match:
        return match.group(1)

    # Regex for 'ifconfig <interface>' (common on BusyBox)
    # Example: inet addr:192.168.1.102  Bcast:192.168.1.255  Mask:255.255.255.0
    # Need to ensure we are in the section for the correct interface.
    # This regex is a bit more complex as ifconfig output can vary.
    # We look for the interface block first.
    ifconfig_interface_block_pattern = re.compile(rf"^{re.escape(interface_name)}\s+.*?Link encap:.*?(?=\n\n|\n^[^\s]|\Z)", re.MULTILINE | re.DOTALL)
    interface_block_match = ifconfig_interface_block_pattern.search(output_str)
    if interface_block_match:
        interface_data = interface_block_match.group(0)
        ifconfig_ip_pattern = re.compile(r"inet addr:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
        ip_match = ifconfig_ip_pattern.search(interface_data)
        if ip_match:
            return ip_match.group(1)
    return None

def get_target_ip(ser, shell_prompt_strs, interface_name, cmd_timeout_s):
    """Gets the IP address of the target for a specific interface."""
    _log(f"Fetching IP address for interface {interface_name}...")
    # Try 'ip addr show' first
    command1 = f"ip addr show {interface_name}"
    output1 = send_command_and_get_output(ser, command1, shell_prompt_strs, prompt_timeout_after_cmd_s=cmd_timeout_s)
    if output1:
        ip = parse_ip_address_from_output(output1, interface_name)
        if ip:
            _log(f"IP address found using '{command1}': {ip}")
            return ip
        else:
            _log(f"Could not parse IP from '{command1}' output. Output:\n{output1}", level="DEBUG")

    # Fallback to 'ifconfig'
    _log(f"Falling back to 'ifconfig {interface_name}' for IP address...")
    command2 = f"ifconfig {interface_name}"
    output2 = send_command_and_get_output(ser, command2, shell_prompt_strs, prompt_timeout_after_cmd_s=cmd_timeout_s)
    if output2:
        ip = parse_ip_address_from_output(output2, interface_name)
        if ip:
            _log(f"IP address found using '{command2}': {ip}")
            return ip
        else:
            _log(f"Could not parse IP from '{command2}' output. Output:\n{output2}", level="DEBUG")

    _log(f"Failed to retrieve IP address for interface {interface_name}.", level="ERROR")
    return None
