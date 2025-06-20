#!/usr/bin/env python3

import time
import subprocess
import sys
import os
import psutil
from obswebsocket import obsws, requests

host = "localhost"
port = 4455
password = ""  # Fill in your password if needed

COOLDOWN_SECONDS = 300  # 5 minutes


def notify(msg):
    try:
        subprocess.Popen(["notify-send", "-a", "OBS Studio", msg])
    except Exception as e:
        print(f"Notification error: {e}")


def is_obs_running():
    for proc in psutil.process_iter(["name", "exe", "cmdline"]):
        try:
            if proc.info["name"] == "obs":
                return True
            if proc.info["exe"] and os.path.basename(proc.info["exe"]) == "obs":
                return True
            if proc.info["cmdline"] and os.path.basename(proc.info["cmdline"][0]) == "obs":
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


def start_obs():
    if is_obs_running():
        print("DEBUG: OBS is already running.")
        return True
    possible_paths = ["/usr/bin/obs", "/usr/local/bin/obs"]
    for path in possible_paths:
        if os.path.exists(path):
            print(f"DEBUG: Launching OBS at {path}...")
            subprocess.Popen([path, "--minimize-to-tray"])
            # Wait a bit for the process to start
            for i in range(10):
                if is_obs_running():
                    print("DEBUG: OBS successfully launched.")
                    return True
                time.sleep(1)
            print("DEBUG: Failed to launch OBS: Process did not appear after 10 seconds.")
            return False
    print("DEBUG: Could not find OBS Studio executable. Please start OBS manually.")
    return False


def close_obs():
    for proc in psutil.process_iter(["name", "pid", "exe", "cmdline"]):
        try:
            if (
                (proc.info["name"] == "obs")
                or (proc.info["exe"] and os.path.basename(proc.info["exe"]) == "obs")
                or (proc.info["cmdline"] and os.path.basename(proc.info["cmdline"][0]) == "obs")
            ):
                print("DEBUG: Closing OBS...")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue


def wait_for_obs_websocket(timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            ws = obsws(host, port, password)
            ws.connect()
            print("DEBUG: Connected to OBS WebSocket.")
            return ws
        except Exception as e:
            print("DEBUG: Waiting for OBS WebSocket...", str(e))
            time.sleep(2)
    print("DEBUG: Failed to connect to OBS WebSocket within timeout.")
    sys.exit(1)


def start_recording(ws):
    print("DEBUG: Starting recording...")
    ws.call(requests.StartRecord())
    notify("OBS: Recording started!")


def stop_recording(ws):
    print("DEBUG: Stopping recording...")
    ws.call(requests.StopRecord())
    notify("OBS: Recording stopped.")


def is_camera_in_use():
    # Only trigger if /dev/video0 is actually in use
    try:
        result = subprocess.run(["fuser", "/dev/video0"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        print(f"DEBUG: fuser /dev/video0 exit code: {result.returncode}")
        if result.returncode == 0:
            print("DEBUG: /dev/video0 is in use (fuser).")
            return True
        else:
            print("DEBUG: /dev/video0 is NOT in use (fuser).")
            return False
    except Exception as e:
        print(f"DEBUG: Exception in fuser: {e}")
        return False


if __name__ == "__main__":
    obs_started = False
    ws = None
    camera_was_on = False
    camera_off_time = None  # When camera was last seen as "off"

    try:
        while True:
            cam_on = is_camera_in_use()
            now = time.time()
            print(f"DEBUG: cam_on = {cam_on}, camera_was_on = {camera_was_on}, camera_off_time = {camera_off_time}")

            if cam_on and not camera_was_on:
                print("DEBUG: Camera detected in use. Launching OBS (if needed)...")
                if not obs_started:
                    obs_started = start_obs()
                    if not obs_started:
                        print("DEBUG: Could not start OBS. Retrying...")
                        time.sleep(5)
                        continue
                    ws = wait_for_obs_websocket(timeout=60)
                if ws:
                    start_recording(ws)
                camera_off_time = None  # cancel any pending OBS shutdown

            elif not cam_on and camera_was_on:
                print("DEBUG: Camera no longer in use. Stopping recording and starting cooldown timer...")
                if ws:
                    stop_recording(ws)
                camera_off_time = now

            elif not cam_on and camera_off_time:
                # If camera has been off long enough, close OBS and reset
                if now - camera_off_time >= COOLDOWN_SECONDS:
                    print(f"DEBUG: Camera unused for {COOLDOWN_SECONDS // 60} minutes. Closing OBS...")
                    if ws:
                        ws.disconnect()
                        ws = None
                    close_obs()
                    obs_started = False
                    camera_off_time = None

            camera_was_on = cam_on
            time.sleep(2)
    except KeyboardInterrupt:
        print("DEBUG: Exiting...")
        if ws:
            stop_recording(ws)
            ws.disconnect()
        if obs_started:
            close_obs()
