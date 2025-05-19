#!/usr/bin/env python3
# status_reporter2.py
# Runs on each LuckFox to gather and publish its status.

import paho.mqtt.client as mqtt
import time
import json
import subprocess
import os
import socket # To get hostname for a default board_id
import sys # For sys.exit

# --- Configuration ---
# MODIFY THIS TO THE IP ADDRESS OF YOUR LUCKFOX RUNNING THE MQTT BROKER
BROKER_IP = "192.168.50.206"  # Example: IP of LF-Display where Mosquitto is running
MQTT_PORT = 1883

# Attempt to use hostname as a default unique ID for this board
try:
    BOARD_ID = socket.gethostname()
except Exception:
    # Fallback if hostname can't be fetched, uses part of current time for some uniqueness
    BOARD_ID = f"luckfox-unknown-{int(time.time()) % 10000}" 

# **IMPORTANT**: For reliable operation, ensure this BOARD_ID is unique for each device.
# If hostnames are not unique (e.g., all are "luckfox"), uncomment and set manually below.
# BOARD_ID = "luckfox-200" # Example: uncomment and set unique ID for each board
print(f"--- Starting Reporter with BOARD_ID: {BOARD_ID} ---")


STATUS_TOPIC = f"luckfox/{BOARD_ID}/status"
REPORT_INTERVAL_S = 15  # How often to report status in seconds

# --- Helper Functions to Get System Stats ---
def get_ip_address(interface="eth0"):
    """Gets the IP address of the specified interface."""
    try:
        # Using 'ip addr' and parsing
        # check=False to prevent raising an exception on non-zero exit, then check result.returncode
        result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"Error getting IP: 'ip addr show {interface}' returned code {result.returncode}")
            return "CmdError"
        for line in result.stdout.split('\n'):
            if 'inet ' in line and 'brd' in line:  # Look for IPv4
                ip = line.split('inet ')[1].split('/')[0]
                return ip
        return "N/A" # Interface might be up but no IP, or IP not found in expected format
    except FileNotFoundError:
        print(f"Error getting IP: 'ip' command not found. Is it in PATH?")
        return "CmdMissing"
    except Exception as e:
        print(f"Generic error getting IP for {interface}: {e}")
        return "Error"

def get_cpu_temperature():
    """Gets the CPU temperature."""
    try:
        # Common path for Rockchip/ARM SBCs
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_milli_c = int(f.read().strip())
        return round(temp_milli_c / 1000.0, 1)
    except FileNotFoundError:
        print("Error: Temperature file not found. Path /sys/class/thermal/thermal_zone0/temp may be incorrect.")
        return "N/A" # Using string "N/A" for consistency in JSON if data missing
    except Exception as e:
        print(f"Error getting CPU temperature: {e}")
        return "Error"

def get_memory_usage():
    """Gets memory usage (UsedM/TotalM)."""
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"Error getting memory: 'free -m' returned code {result.returncode}")
            return "CmdError"
        lines = result.stdout.split('\n')
        # Standard 'free -m' output (e.g., from GNU coreutils version)
        if len(lines) > 1 and lines[1].startswith("Mem:"):
            parts = lines[1].split() # e.g. ['Mem:', '960', '120', '840', '0', '200', '800']
            if len(parts) >= 3: # Need at least Mem: Total Used Free
                return f"{parts[2]}M/{parts[1]}M" # UsedM/TotalM
        # Attempt to parse BusyBox 'free' output (often different format, values in KB)
        # Example: Mem: 83480 34360 49120 0 4940 25000 (Total, Used, Free, Shared, Buff, Cached in KB)
        elif len(lines) > 1 and "Mem:" in lines[0] and "Swap:" in lines[1]: 
             mem_line = lines[0] # First line should be Mem: Total Used Free ...
             parts = mem_line.split()
             if len(parts) >= 4 and parts[0] == "Mem:": # Mem: Total Used Free
                 total_kb = int(parts[1])
                 used_kb = int(parts[2])
                 return f"{round(used_kb/1024)}M/{round(total_kb/1024)}M" # Convert KB to MB for consistency
        print("Could not parse 'free -m' output format.")
        return "N/A"
    except FileNotFoundError:
        print(f"Error getting memory: 'free' command not found.")
        return "CmdMissing"
    except Exception as e:
        print(f"Error getting memory usage: {e}")
        return "Error"

def get_uptime_hours():
    """Gets system uptime in hours."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
        hours = int(uptime_seconds / 3600)
        return hours
    except FileNotFoundError:
        print("Error: Uptime file /proc/uptime not found.")
        return "N/A"
    except Exception as e:
        print(f"Error getting uptime: {e}")
        return "Error"

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc, properties=None):
    # properties argument is part of the paho.mqtt.client.CallbackAPIVersion.VERSION2 signature
    if rc == 0:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully connected to MQTT Broker at {BROKER_IP} as {BOARD_ID}")
    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to connect to MQTT Broker, rc {rc} ({mqtt.connack_string(rc)})")

def on_disconnect(client, userdata, rc, properties=None, *args): # Adjusted to accept more args
    disconnect_reason = rc
    if hasattr(rc, 'getName'): # Check if rc is a ReasonCode object (Paho v2.x)
        disconnect_reason = rc.getName()
    elif isinstance(rc, int): # If it's an int (older Paho or simple disconnect)
        disconnect_reason = f"Code: {rc}"
        
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Disconnected from MQTT Broker. Reason: {disconnect_reason}")
    if properties or args: # Check if properties (MQTTv5) or other args were passed
        print(f"  Extra disconnect info: properties={properties}, args={args}")
    # loop_start() which is used below should handle reconnection attempts.

def on_publish(client, userdata, mid, properties=None, reason_code=None):
    # This callback is triggered when a message with QoS > 0 has been acknowledged by the broker (for QoS 1 & 2)
    # or when it has left the client (for QoS 0).
    # For this script, we primarily check the return code of client.publish() directly.
    # You could add logging here if needed:
    # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Message {mid} confirmed published.")
    pass

# --- Main ---
if __name__ == "__main__":
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{BOARD_ID}-reporter")
    
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_publish = on_publish

    # Optional: Enable Paho logging for deep debugging connection/publish issues
    # import logging
    # logging.basicConfig(level=logging.DEBUG) # You can set this to INFO or WARNING
    # mqtt_client.enable_logger(logging.getLogger(__name__))

    connection_attempts = 0
    max_connection_attempts = 5 # Try to connect 5 times before giving up
    
    while not mqtt_client.is_connected() and connection_attempts < max_connection_attempts:
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Attempting to connect to MQTT Broker at: {BROKER_IP}:{MQTT_PORT} (Attempt {connection_attempts + 1}/{max_connection_attempts})")
            mqtt_client.connect(BROKER_IP, MQTT_PORT, keepalive=60) # 60s keepalive
            mqtt_client.loop_start() # Start non-blocking network loop
            
            # Wait a moment for connection to establish or fail clearly
            connect_wait_start = time.time()
            while not mqtt_client.is_connected() and (time.time() - connect_wait_start) < 10: # Wait up to 10s
                time.sleep(0.1)

            if mqtt_client.is_connected():
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection successful on attempt {connection_attempts + 1}.")
                break # Exit connection loop
            else:
                # If still not connected, stop the loop for this attempt to prevent multiple loops running
                mqtt_client.loop_stop(force=True) # force=True if connect failed badly
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection attempt {connection_attempts + 1} timed out or failed to establish.")

        except ConnectionRefusedError:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection refused. Is the MQTT broker ({BROKER_IP}) running and configured for LAN access?")
        except socket.gaierror: # Hostname resolution error
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Broker IP address '{BROKER_IP}' could not be resolved. Check network/DNS.")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error during MQTT connect attempt: {e}")
        
        connection_attempts += 1
        if not mqtt_client.is_connected() and connection_attempts < max_connection_attempts:
             print(f"Will retry connection in 5 seconds...")
             time.sleep(5)

    if not mqtt_client.is_connected():
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to connect to MQTT broker after {max_connection_attempts} attempts. Exiting.")
        sys.exit(1)

    try:
        while True:
            # Check connection before attempting to publish
            if not mqtt_client.is_connected():
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Not connected to broker. Publish will likely fail. Paho loop should be attempting reconnect.")
                # Depending on how Paho's auto-reconnect is behaving, you might add explicit reconnect here,
                # but usually loop_start() handles it for many network interruptions.
                # A robust solution would have more state management around reconnections.
                time.sleep(REPORT_INTERVAL_S / 2) # Wait a bit less if disconnected to allow quicker reconnect check
                continue # Skip this publish cycle, try again after sleep

            ip_addr = get_ip_address()
            cpu_temp = get_cpu_temperature()
            mem_usage = get_memory_usage() # Expected format like "UsedM/TotalM"
            uptime_h = get_uptime_hours()   # Get uptime in hours

            status_payload = {
                "board_id": BOARD_ID,
                "ip": ip_addr,
                "temp_c": cpu_temp,
                "mem_usage_str": mem_usage, # Send the string directly
                "uptime_h": uptime_h,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }
            payload_json = json.dumps(status_payload)
            
            msg_info = mqtt_client.publish(STATUS_TOPIC, payload_json, qos=1) # QoS 1 for "at least once"
            
            if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
                # For QoS 1, this means the message has been accepted by the client library for delivery.
                # Confirmation from broker comes via on_publish if mid is tracked.
                print(f"[{status_payload['timestamp']}] Data for {BOARD_ID} queued for publish to {STATUS_TOPIC}.")
            else:
                print(f"[{status_payload['timestamp']}] FAILED to publish for {BOARD_ID}. MQTT RC: {msg_info.rc} ({mqtt.error_string(msg_info.rc)})")

            time.sleep(REPORT_INTERVAL_S)

    except KeyboardInterrupt:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Status reporter stopping due to user request...")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] An unhandled error occurred in the main loop: {e}")
    finally:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Shutting down reporter for {BOARD_ID}...")
        if mqtt_client: 
            mqtt_client.loop_stop(force=False) # Allow time for graceful disconnect
            if mqtt_client.is_connected(): # Check before calling disconnect
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Disconnecting from broker...")
                mqtt_client.disconnect()
            else:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Already disconnected or was never fully connected.")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Reporter for {BOARD_ID} fully stopped.")

