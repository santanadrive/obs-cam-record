# OBS Camera Recorder Autostart (Fedora, Wayland/KDE)

This project provides a **background Python automation script** and a **systemd user service** that automatically launches OBS Studio, starts a screen/camera recording when your webcam is in use, and stops/cleans up after your camera is off. It's designed for Fedora Linux (KDE/Wayland or X11) and works perfectly with user logins and desktop notifications.

---

## Features

- **Automatic camera detection**: Starts recording only when the webcam is in use by applications (Teams, Zoom, etc).
- **OBS autostart**: Launches OBS Studio in the background if needed.
- **Smart cleanup**: Stops recording and closes OBS after your camera is unused for a set period.
- **Desktop notifications**: Sends system notifications (using `notify-send`) when recording starts/stops.
- **Robust error handling & debugging output**.
- **Systemd user service**: Automatically starts at login, restarts on crash, runs in the user's graphical session.

---

## Requirements

- Fedora Linux (KDE or GNOME; tested on Fedora 39/40/42)
- Python 3
- `obswebsocket` Python package (`pip install obs-websocket-py`)
- OBS Studio installed (`dnf install obs-studio`)
- `notify-send` available (`dnf install libnotify`)
- `psutil` Python package (`pip install psutil`)

---

## Installation & Setup

### 1. Clone or copy the script

Save your script to (for example):

```
/home/santana/Github/obs-cam-record/Fedora/obs_cam_record.py
```

### 2. Install requirements

```
pip install obs-websocket-py psutil
sudo dnf install obs-studio libnotify
```

### 3. Enable the OBS WebSocket plugin in OBS

- Launch OBS Studio
- Open **Tools > WebSocket Server Settings**
- Make sure it is enabled and running on port `4455` (default for OBS 28+)

### 4. Create the systemd user service

Create the file:

```
~/.config/systemd/user/obs-cam-record.service
```

Example contents:

```
[Unit]
Description=OBS Camera Recorder Autostart

[Service]
ExecStart=/usr/bin/python3 /home/santana/Github/obs-cam-record/Fedora/obs_cam_record.py
Restart=always
RestartSec=5
Environment="DISPLAY=:0"
Environment="WAYLAND_DISPLAY=wayland-0"

[Install]
WantedBy=default.target
```

> **TIP:** Double-check `$DISPLAY` and `$WAYLAND_DISPLAY` values by running `echo $DISPLAY` and `echo $WAYLAND_DISPLAY` in your graphical session.

### 5. Enable and start the service

```
systemctl --user daemon-reload
systemctl --user enable --now obs-cam-record.service
```

---

## Usage & Behavior

- Script runs in the background after you log in.
- When any app starts using `/dev/video0` (your webcam), OBS is launched and begins recording.
- When your webcam is **no longer in use**, OBS will stop recording and—after a 5-minute cooldown—will automatically close.
- Notifications will alert you whenever recording **starts** or **stops**.
- The script will **auto-restart** if it crashes.
- Logs can be monitored with:

  ```sh
  journalctl --user -u obs-cam-record.service -f
  ```

---

## Troubleshooting

- If OBS crashes on startup or fails to display, make sure you are running in a real graphical session and not via SSH or a virtual console.
- If notifications don't appear, check notification settings and ensure `notify-send` is installed.
- If your camera device is not `/dev/video0`, adjust the script as needed.
- The script and OBS must run in the same user session that owns the display.

---

## Customization

- **COOLDOWN_SECONDS**: Change the number of seconds OBS will wait after the camera is unused before closing (default: 300 = 5 minutes).
- **Notification text**: Modify calls to `notify("...")` in the script for personalized messages.

---

## Uninstallation

To disable and remove the autostart:

```
systemctl --user stop obs-cam-record.service
systemctl --user disable obs-cam-record.service
rm ~/.config/systemd/user/obs-cam-record.service
```

And (optionally) remove the script file.
