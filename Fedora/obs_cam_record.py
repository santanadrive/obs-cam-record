#!/usr/bin/env python3

import time
import subprocess
import sys
import os
import glob
import psutil
from obswebsocket import obsws, requests
from dotenv import load_dotenv

load_dotenv()

# ===============================
# Environment Variables
# ===============================

HOST = os.getenv("OBS_HOST")
PORT = int(os.getenv("OBS_PORT"))
PASSWORD = os.getenv("OBS_PASSWORD")

CAMERA_DEVICE = os.getenv("CAMERA_DEVICE")

CAMERA_STABILITY_SECONDS = float(os.getenv("CAMERA_STABILITY_SECONDS"))
CHECK_INTERVAL_SECONDS = float(os.getenv("CHECK_INTERVAL_SECONDS"))

COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS"))

RECORDINGS_DIR = os.getenv("RECORDINGS_DIR")

# ===============================


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
            ws = obsws(HOST, PORT, PASSWORD)
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


def get_latest_recording(directory, extlist=("mp4", "mkv")):
    files = []
    for ext in extlist:
        files += glob.glob(os.path.join(directory, f"*.{ext}"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def prompt_for_comment():
    try:
        comment = subprocess.check_output(
            ["zenity", "--entry", "--title=Recording Summary Comment", "--text=Enter a summary for your recording:"], universal_newlines=True
        ).strip()
        return comment
    except Exception as e:
        print("DEBUG: Zenity popup failed or cancelled:", e)
        return None


def write_comment_to_file(filepath, comment):
    try:
        subprocess.run(["exiftool", f"-comment={comment}", "-overwrite_original", filepath], check=True)
        print("DEBUG: Comment written to", filepath)
    except Exception as e:
        print("DEBUG: exiftool failed:", e)


def stop_recording(ws, recordings_dir):
    print("DEBUG: Stopping recording...")
    ws.call(requests.StopRecord())
    notify("OBS: Recording stopped.")
    # Wait for file to be fully written
    time.sleep(2)
    latest_file = get_latest_recording(recordings_dir)
    if latest_file:
        comment = prompt_for_comment()
        if comment:
            write_comment_to_file(latest_file, comment)


def is_camera_in_use():
    try:
        result = subprocess.run(
            ["fuser", CAMERA_DEVICE],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        print(f"DEBUG: fuser {CAMERA_DEVICE} exit code: {result.returncode}")
        if result.returncode == 0:
            print(f"DEBUG: {CAMERA_DEVICE} is in use (fuser).")
            return True
        else:
            return False
    except Exception as e:
        print(f"DEBUG: Exception in fuser: {e}")
        return False


if __name__ == "__main__":
    obs_started = False
    ws = None
    camera_was_on = False
    camera_off_time = None

    try:
        while True:
            cam_on = is_camera_in_use()
            now = time.time()
            print(f"DEBUG: cam_on = {cam_on}, camera_was_on = {camera_was_on}, camera_off_time = {camera_off_time}")

            if cam_on and not camera_was_on:
                print("DEBUG: Camera detected in use. Monitoring for 2 seconds to confirm...")

                activation_time = time.time()
                while time.time() - activation_time < CAMERA_STABILITY_SECONDS:
                    # If camera turns off during this window, abort
                    if not is_camera_in_use():
                        print("DEBUG: Camera did not stay active for 2 seconds — skipping recording.")
                        cam_on = False  # <-- keep state consistent so we don't trigger stop later
                        break
                    time.sleep(CHECK_INTERVAL_SECONDS)
                else:
                    # Only triggered if the camera stayed on for the full 2 seconds
                    print("DEBUG: Camera stayed active for 2 seconds — proceeding to record.")
                    if not obs_started:
                        obs_started = start_obs()
                        if not obs_started:
                            print("DEBUG: Could not start OBS. Retrying...")
                            time.sleep(5)
                            continue
                        ws = wait_for_obs_websocket(timeout=60)
                    if ws:
                        start_recording(ws)
                    camera_off_time = None

            elif not cam_on and camera_was_on:
                print("DEBUG: Camera no longer in use. Stopping recording and starting cooldown timer...")
                if ws:
                    stop_recording(ws, RECORDINGS_DIR)
                camera_off_time = now

            elif not cam_on and camera_off_time:
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
            stop_recording(ws, RECORDINGS_DIR)
            ws.disconnect()
        if obs_started:
            close_obs()
