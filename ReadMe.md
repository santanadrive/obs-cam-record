# OBS Auto Screen Recorder

Automatically starts and stops OBS Studio screen recording based on camera activity (Teams, Zoom, etc.) on Windows.

---

## 📋 What It Does

- **Monitors** for use of your camera by common apps (Teams, Zoom, Skype, Windows Camera, etc.).
- **Launches OBS Studio (minimized)** and starts screen recording **whenever the camera is detected in use**.
- **Stops recording** when the camera is no longer in use.
- **Keeps OBS running** for 5 minutes after camera stops (in case you re-join a call), then closes OBS if unused.

---

## 🖥️ How It Works

- The script checks for running processes that typically use your camera.
- When it detects a process, it ensures OBS is open (minimized), then connects to OBS's WebSocket server and starts recording.
- When all camera-using processes close, it stops the recording, then starts a 5-minute "cooldown."
- If the camera is not used for 5 minutes, OBS is closed. If the camera is used again before 5 minutes, OBS continues running and recording resumes.

---

## 🚦 Requirements

- **Windows 10 or 11**
- **OBS Studio** (install from [obsproject.com](https://obsproject.com/))
- **OBS WebSocket** plugin (built into OBS v28+; enable in Tools > WebSocket Server Settings)
- **Python 3.8+** (install from [python.org](https://python.org/downloads/))

  - Make sure to check **"Add Python to PATH"** during install

- **Python packages**:
  Open Command Prompt and run:

  ```sh
  pip install obs-websocket-py psutil
  ```

---

## ⚙️ Setup Instructions

### 1. Configure OBS Studio

- Install OBS Studio from [obsproject.com](https://obsproject.com/).
- Open OBS, go to **Tools → WebSocket Server Settings**.
- Make sure **"Enable WebSocket server"** is checked.

  - Default port: `4455`
  - Optionally, set a password (if you do, update your Python script).

- Click OK.

### 2. Set up your recording scene in OBS

- In OBS, add a **Display Capture** source to the default Scene (this is required to record your desktop!).
- Arrange any audio/video sources as desired.

### 3. Install Python and required packages

- Download and install Python from [python.org](https://python.org/downloads/).
- In the Python installer, check **"Add Python to PATH"**.
- Open Command Prompt and run:

  ```sh
  pip install obs-websocket-py psutil
  ```

### 4. Save and Configure the Script

- Save the Python script (`obs_cam_record.py`) somewhere safe (e.g., `C:\Users\YourName\Python\auto-record\obs_cam_record.py`).
- Edit the script:

  - If you set an OBS WebSocket password, update the `password` variable.
  - Add/remove camera process names as needed for your environment.

### 5. Run as a Background Service (Windows Task Scheduler)

#### Set up with Task Scheduler:

1. **Open Task Scheduler** (`Win + R` → `taskschd.msc`)
2. **Create Task** (not Basic Task)
3. **General Tab:**

   - Name: `OBS Auto Recorder`
   - Optionally, select **Run whether user is logged on or not** and **Run with highest privileges**.

4. **Triggers Tab:**

   - New → **At log on** (for your user or all users)

5. **Actions Tab:**

   - Action: **Start a program**
   - **Program/script:**

     - Use `pythonw.exe` (no console popup):
       `C:\Users\YourName\AppData\Local\Programs\Python\Python3xx\pythonw.exe`

   - **Add arguments:**
     `"C:\Users\YourName\Python\auto-record\obs_cam_record.py"`
   - **Start in:**
     `C:\Users\YourName\Python\auto-record`

6. **OK/Save**. Enter your Windows password if prompted.

---

## ✅ Done!

- The script will now run invisibly at every logon, launching OBS and recording your screen only when the camera is used by Teams/Zoom/etc.
- OBS will close itself if unused for 5 minutes.

---

## 🛠️ Troubleshooting

- **Script not recording?**

  - Check the OBS scene has a Display Capture source.
  - Make sure WebSocket is enabled and the port/password match your script.

- **Want to change camera-detecting processes?**

  - Edit the `camera_processes` list in the script.

- **To uninstall:** Delete the scheduled task and script files.
