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


def start_obs():
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and "obs64.exe" in proc.info["name"].lower():
            print("OBS is already running.")
            return True
    possible_paths = [r"C:\Program Files\obs-studio\bin\64bit\obs64.exe", r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe"]
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Launching OBS at {path}...")
            subprocess.Popen([path, "--minimize-to-tray"], cwd=os.path.dirname(path))
            return True
    print("Could not find OBS Studio executable. Please start OBS manually.")
    return False


def close_obs():
    for proc in psutil.process_iter(["name", "pid"]):
        if proc.info["name"] and "obs64.exe" in proc.info["name"].lower():
            print("Closing OBS...")
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
            break


def wait_for_obs_websocket(timeout=60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            ws = obsws(host, port, password)
            ws.connect()
            print("Connected to OBS WebSocket.")
            return ws
        except Exception as e:
            print("Waiting for OBS WebSocket...", str(e))
            time.sleep(2)
    print("Failed to connect to OBS WebSocket within timeout.")
    sys.exit(1)


def start_recording(ws):
    print("Starting recording...")
    ws.call(requests.StartRecord())


def stop_recording(ws):
    print("Stopping recording...")
    ws.call(requests.StopRecord())


def is_camera_in_use():
    camera_processes = ["Teams", "Zoom", "Skype", "WindowsCamera"]  # Add as needed
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and any(p in proc.info["name"] for p in camera_processes):
            return True
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

            if cam_on and not camera_was_on:
                print("Camera detected in use. Launching OBS (if needed)...")
                if not obs_started:
                    obs_started = start_obs()
                    ws = wait_for_obs_websocket(timeout=60)
                start_recording(ws)
                camera_off_time = None  # cancel any pending OBS shutdown

            elif not cam_on and camera_was_on:
                print("Camera no longer in use. Stopping recording and starting cooldown timer...")
                if ws:
                    stop_recording(ws)
                camera_off_time = now

            elif not cam_on and camera_off_time:
                # If camera has been off long enough, close OBS and reset
                if now - camera_off_time >= COOLDOWN_SECONDS:
                    print(f"Camera unused for {COOLDOWN_SECONDS // 60} minutes. Closing OBS...")
                    if ws:
                        ws.disconnect()
                        ws = None
                    close_obs()
                    obs_started = False
                    camera_off_time = None

            camera_was_on = cam_on
            time.sleep(2)
    except KeyboardInterrupt:
        print("Exiting...")
        if ws:
            stop_recording(ws)
            ws.disconnect()
        if obs_started:
            close_obs()
