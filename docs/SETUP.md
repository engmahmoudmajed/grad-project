# Setup & Assembly Guide 🛠️

Complete guide to build, wire, and run the **Fruit Classification System** on a Raspberry Pi 5.

---

## Table of Contents

1. [Bill of Materials](#1-bill-of-materials)
2. [Hardware Assembly](#2-hardware-assembly)
3. [Wiring Diagram (GPIO)](#3-wiring-diagram-gpio)
4. [Raspberry Pi OS Setup](#4-raspberry-pi-os-setup)
5. [Software Installation](#5-software-installation)
6. [Font Assets](#6-font-assets)
7. [Camera Calibration](#7-camera-calibration)
8. [Running the System](#8-running-the-system)
9. [Live Monitor (Web)](#9-live-monitor-web)
10. [Configuration Reference](#10-configuration-reference)
11. [Troubleshooting](#11-troubleshooting)
12. [Auto-Start on Boot](#12-auto-start-on-boot)

---

## 1. Bill of Materials

| #  | Component                                           | Qty | Notes                                  |
|----|-----------------------------------------------------|-----|----------------------------------------|
| 1  | Raspberry Pi 5 Model B – 8 GB RAM                  | 1   | Made in UK edition                     |
| 2  | Raspberry Pi Camera Module V2 (IMX219, 8 MP)        | 1   | Official, connects to CAM0 port        |
| 3  | Raspberry Pi Camera Module (OV5647, 5 MP)           | 1   | Connects to CAM1 port                  |
| 4  | 15-pin CSI Camera Ribbon Cable                      | 2   | One per camera                         |
| 5  | 4×4 Matrix Membrane Keypad                          | 1   | 8-pin header                           |
| 6  | 4-Channel Relay Module (5 V, active-HIGH)           | 1   | Normally-Open wiring                   |
| 7  | IR Obstacle Sensor Module (e.g. FC-51)              | 1   | LOW output when object detected        |
| 8  | SH1106 / SSD1306 OLED Display (128×64, I2C)         | 1   | I2C address `0x3C`                     |
| 9  | Conveyor Belt with Motor                            | 1   | Fixed speed                            |
| 10 | 3 × Sorting Gates / Flaps                           | 3   | Driven by Relays 1-3                   |
| 11 | 5 V / 3 A USB-C Power Supply (for Pi)               | 1   |                                        |
| 12 | Jumper Wires (Male-Female)                          | ~20 |                                        |
| 13 | Breadboard (optional)                               | 1   | For prototyping                        |
| 14 | MicroSD Card (32 GB+)                               | 1   | For Raspberry Pi OS                    |

---

## 2. Hardware Assembly

### 2.1 Mount the Cameras

1. **CAM0 port** → Connect the **IMX219** (8 MP) camera using a CSI ribbon cable.
2. **CAM1 port** → Connect the **OV5647** (5 MP) camera using a CSI ribbon cable.
3. Position both cameras directly **above the conveyor belt**, pointing downward at the fruit.
4. Ensure consistent camera height — the calibration step depends on this.

> **Tip:** Secure the cameras with a mounting bracket or 3D-printed enclosure so the distance to the belt surface stays constant.

### 2.2 Mount the IR Sensor

1. Place the IR sensor at the **start of the conveyor belt** (before the camera capture zone).
2. The IR beam should cross the belt path so that passing fruit breaks the beam.
3. Adjust sensitivity with the on-board potentiometer until it reliably triggers.

### 2.3 Attach the Relay Module & Sorting Gates

1. Mount the 4-channel relay module near the Pi.
2. Connect the three sorting gates/flaps to **Relay 1, 2, and 3** output terminals.
3. Gates are positioned along the belt **after** the camera zone:
   - **Gate 1 (Relay 1)** → Small fruit, activates **5 s** after IR trigger
   - **Gate 2 (Relay 2)** → Medium fruit, activates **10 s** after IR trigger
   - **Gate 3 (Relay 3)** → Big fruit, activates **15 s** after IR trigger
   - **Relay 4** → Reserved for future use / reject lane.

### 2.4 Connect the Keypad

Attach the 8-pin 4×4 membrane keypad to the GPIO header using jumper wires (see wiring table below).

### 2.5 Connect the OLED Display

Connect the 4-pin I2C OLED display:
- **VCC** → 3.3 V (Pin 1)
- **GND** → Ground (Pin 6)
- **SDA** → GPIO 2 (Pin 3)
- **SCL** → GPIO 3 (Pin 5)

---

## 3. Wiring Diagram (GPIO)

All pin numbers use **BCM numbering**.

### Complete Wiring Table

| Component        | Part / Function | GPIO (BCM) | Direction | Physical Pin |
|------------------|-----------------|------------|-----------|--------------|
| **4×4 Keypad**   | Row 1           | 18         | Output    | 12           |
|                  | Row 2           | 23         | Output    | 16           |
|                  | Row 3           | 24         | Output    | 18           |
|                  | Row 4           | 25         | Output    | 22           |
|                  | Column 1        | 10         | Input     | 19           |
|                  | Column 2        | 22         | Input     | 15           |
|                  | Column 3        | 27         | Input     | 13           |
|                  | Column 4        | 17         | Input     | 11           |
| **Relay Module** | Relay 1 (Small) | 16         | Output    | 36           |
|                  | Relay 2 (Med)   | 20         | Output    | 38           |
|                  | Relay 3 (Big)   | 21         | Output    | 40           |
|                  | Relay 4 (Spare) | 19         | Output    | 35           |
| **IR Sensor**    | Signal Out      | 26         | Input     | 37           |
| **OLED Display** | SDA (Data)      | 2          | I2C       | 3            |
|                  | SCL (Clock)     | 3          | I2C       | 5            |

### Relay Configuration

- **Wiring type:** Normally-Open (NO)
- **Logic:** Active-HIGH → `GPIO HIGH = relay ON`
- Can be changed to active-LOW in `config.py` → `RELAY_ACTIVE_LOW = True`

### Keypad Layout

```
┌─────┬─────┬─────┬─────┐
│  1  │  2  │  3  │  A  │
├─────┼─────┼─────┼─────┤
│  4  │  5  │  6  │  B  │
├─────┼─────┼─────┼─────┤
│  7  │  8  │  9  │  C  │
├─────┼─────┼─────┼─────┤
│  *  │  0  │  #  │  D  │
└─────┴─────┴─────┴─────┘
```

Press **C** then a **digit (1–9)** to select produce type.

---

## 4. Raspberry Pi OS Setup

### 4.1 Flash the OS

1. Download **Raspberry Pi OS (64-bit, Bookworm)** from [raspberrypi.com](https://www.raspberrypi.com/software/)
2. Flash to MicroSD using **Raspberry Pi Imager**.
3. Enable SSH, set hostname, and configure Wi-Fi during flashing.

### 4.2 Enable Required Interfaces

After first boot, run:

```bash
sudo raspi-config
```

Enable the following under **Interface Options**:

| Interface | Purpose              |
|-----------|----------------------|
| I2C       | OLED display         |
| Camera    | Both CSI cameras     |
| SSH       | Remote access        |

Reboot after enabling:

```bash
sudo reboot
```

### 4.3 Verify Cameras Are Detected

```bash
# List all connected cameras
libcamera-hello --list-cameras
```

You should see **two cameras** listed (e.g., `imx219` on cam0 and `ov5647` on cam1).

### 4.4 Verify I2C (OLED)

```bash
sudo apt install -y i2c-tools
i2cdetect -y 1
```

You should see a device at address `0x3C`.

---

## 5. Software Installation

### 5.1 Clone the Repository

```bash
git clone <repository-url>
cd grad-project
```

### 5.2 Create a Virtual Environment

The `--system-site-packages` flag is **required** so that the venv can access system-level packages like `picamera2`, `lgpio`, and `RPi.GPIO` that cannot be installed via pip.

```bash
python3 -m venv venv --system-site-packages
source venv/bin/activate
```

### 5.3 Install Python Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** Some packages (e.g. `torch`, `ultralytics`, `opencv-python`) are large and may take several minutes to install on a Pi.

### 5.4 Key Dependencies Summary

| Package          | Purpose                         |
|------------------|---------------------------------|
| `picamera2`      | Pi camera control               |
| `opencv-python`  | Image processing, contour detection |
| `ultralytics`    | YOLOv8 fruit detection          |
| `torch`          | PyTorch backend for YOLO        |
| `luma.oled`      | SH1106 OLED display driver      |
| `lgpio`          | GPIO control (Pi 5 compatible)  |
| `Pillow`         | Image rendering for OLED        |
| `Flask`          | (Dependency, not directly used) |
| `numpy`          | Array operations                |

---

## 6. Font Assets

The OLED display uses custom fonts for icons and text. Download and place them in the `assets/` folder:

| File                        | Source                                                              |
|-----------------------------|---------------------------------------------------------------------|
| `PixelOperator.ttf`         | [dafont.com/pixel-operator.font](https://www.dafont.com/pixel-operator.font) |
| `lineawesome-webfont.ttf`   | [icons8.com/line-awesome](https://icons8.com/line-awesome) (download the webfont package) |

```bash
# Verify fonts are in place
ls assets/
# Should show: PixelOperator.ttf  lineawesome-webfont.ttf  README.md
```

> If fonts are missing, the system will fall back to PIL's built-in default font. Icons won't display, but text will still work.

---

## 7. Camera Calibration

Calibration converts pixel measurements to real-world millimeters. **This is critical for accurate sizing.**

### 7.1 Run the Calibration Script

```bash
source venv/bin/activate
python calibrate.py
```

### 7.2 Steps

1. Place a **flat object of known width** (ruler, coin, credit card) on the belt, at the same height and position where fruit will be.
2. Select a produce type for auto-detection, or choose `0` for manual mode.
3. Press **ENTER** — the camera captures a frame.
4. The script tries YOLO detection first, then OpenCV contour detection.
5. Enter the **actual width of the object in millimeters**.
6. The script computes `PIXELS_PER_MM` and writes it directly into `config.py`.

### 7.3 Verify

Open `config.py` and check the updated line:

```python
PIXELS_PER_MM     = 5.1234  # Calibrated by calibrate.py
```

> **Re-calibrate if you change the camera height or position.**

---

## 8. Running the System

### 8.1 Start the Main Sorter

```bash
source venv/bin/activate
python main.py
```

The system will:
1. Initialize all hardware modules (cameras, keypad, OLED, relays, IR sensor)
2. Start the live monitor web server (port `8080`)
3. Display system stats on the OLED
4. Wait for fruit to pass the IR sensor

### 8.2 Operation Flow

```
┌─────────────────┐
│  Select Produce  │  Press C + digit (1-9) on keypad
│  (Keypad)        │  Default: Apple (1)
└───────┬─────────┘
        ▼
┌─────────────────┐
│  IR Sensor       │  Fruit breaks the beam
│  Triggers        │
└───────┬─────────┘
        ▼
┌─────────────────┐
│  Camera Capture  │  Both cameras grab a frame
│  + AI Detection  │  YOLO → OpenCV fallback
└───────┬─────────┘
        ▼
┌─────────────────┐
│  Classify Size   │  Compare mm to produce size table
│  S / M / L       │
└───────┬─────────┘
        ▼
┌─────────────────┐
│  Activate Relay  │  After timed delay:
│  (Sorting Gate)  │  Small→5s, Medium→10s, Big→15s
└───────┬─────────┘
        ▼
┌─────────────────┐
│  OLED Display    │  Shows result for 3 seconds
│  Shows Result    │
└─────────────────┘
```

### 8.3 Produce Selection (Keypad)

Press **C** followed by a digit to select the produce type:

| Key Combo | Produce      |
|-----------|--------------|
| C + 1     | Apple        |
| C + 2     | Orange       |
| C + 3     | Banana       |
| C + 4     | Tomato       |
| C + 5     | Potato       |
| C + 6     | Onion        |
| C + 7     | Bell Pepper  |
| C + 8     | Cucumber     |
| C + 9     | Lemon        |

---

## 9. Live Monitor (Web)

The system includes a built-in MJPEG web server that streams both camera feeds live.

### Auto-Start (with main.py)

The monitor starts automatically when you run `main.py`. Open your browser:

```
http://<raspberry-pi-ip>:8080
```

### Standalone Mode

```bash
source venv/bin/activate
python monitor/server.py
```

The monitor page shows:
- **Camera 0** (IMX219) — live stream
- **Camera 1** (OV5647) — live stream
- **Best Result** — last detection frame from `main.py`

---

## 10. Configuration Reference

All settings are in **`config.py`**. Key parameters you might want to adjust:

### Timing

| Constant              | Default | Description                              |
|-----------------------|---------|------------------------------------------|
| `RELAY_DELAYS`        | 5/10/15 | Seconds after IR trigger before relay fires |
| `RELAY_PULSE_DURATION`| 5       | How long the relay stays ON (seconds)    |
| `IR_DEBOUNCE_SECS`    | 1.0     | Ignore re-triggers within this window    |
| `OLED_EVENT_SECS`     | 3       | How long to display event on OLED        |

### Detection

| Constant          | Default         | Description                             |
|-------------------|-----------------|-----------------------------------------|
| `USE_YOLO`        | `True`          | Use YOLOv8 (set `False` for OpenCV-only) |
| `YOLO_MODEL`      | `yolov8n.pt`    | Model file (auto-downloads on first run) |
| `YOLO_CONFIDENCE` | `0.20`          | Minimum detection confidence (0–1)       |
| `PIXELS_PER_MM`   | `5.0`           | Set via `calibrate.py`                   |
| `DEFAULT_SIZE_MM` | `70.0`          | Fallback if cameras fail (0 = disabled)  |

### Hardware

| Constant            | Default         | Description                          |
|---------------------|-----------------|--------------------------------------|
| `RELAY_ACTIVE_LOW`  | `False`         | `True` for active-LOW relay boards   |
| `OLED_I2C_ADDRESS`  | `0x3C`          | Try `0x3D` if OLED stays black       |

---

## 11. Troubleshooting

### Cameras

| Problem                    | Solution                                                    |
|----------------------------|-------------------------------------------------------------|
| Camera not detected        | Check ribbon cable orientation and run `libcamera-hello --list-cameras` |
| Only one camera works      | Verify both CSI ports are enabled in `raspi-config`         |
| Blurry images              | Adjust focus ring on the camera module                      |
| Wrong pixel-to-mm ratio    | Re-run `python calibrate.py`                                |

### OLED Display

| Problem                    | Solution                                                    |
|----------------------------|-------------------------------------------------------------|
| Screen stays black         | Check I2C wiring; try `i2cdetect -y 1`; try address `0x3D` |
| No icons shown             | Download font files to `assets/` (see Section 6)            |
| Garbled display            | Confirm display is SH1106, not SSD1306 (change driver in code if needed) |

### Relays

| Problem                       | Solution                                                 |
|-------------------------------|----------------------------------------------------------|
| Relay clicks but gate doesn't move | Check Normally-Open wiring at relay terminal            |
| Relay never fires             | Check `RELAY_ACTIVE_LOW` in `config.py`; test with `lgpio` directly  |
| Wrong gate opens              | Verify GPIO assignments in `RELAY_PINS` match physical wiring        |

### Software

| Problem                             | Solution                                              |
|--------------------------------------|-------------------------------------------------------|
| `ModuleNotFoundError: lgpio`         | Ensure venv was created with `--system-site-packages`  |
| `ModuleNotFoundError: picamera2`     | Same as above; `picamera2` is a system package         |
| YOLO model download fails           | Check internet; or manually download `yolov8n.pt` from [Ultralytics](https://github.com/ultralytics/assets/releases) |
| `RuntimeError: No cameras could be opened!` | Both cameras failed — check cables and reboot    |

### Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

Tests can run on **any machine** (no hardware needed) — they mock GPIO and camera modules.

---

## 12. Auto-Start on Boot

To make the fruit sorter start automatically every time the Raspberry Pi boots:

### One-Command Install

```bash
sudo bash scripts/install-service.sh
```

This copies the systemd service file, enables it, and starts it immediately.

### Managing the Service

| Command | Action |
|---------|--------|
| `sudo systemctl status fruit-sorter` | Check if it's running |
| `sudo systemctl stop fruit-sorter` | Stop the service |
| `sudo systemctl restart fruit-sorter` | Restart after config changes |
| `sudo journalctl -u fruit-sorter -f` | View live logs |
| `sudo systemctl disable fruit-sorter` | Disable auto-start (keeps service) |

### Uninstall

To completely remove auto-start:

```bash
sudo bash scripts/uninstall-service.sh
```

> **Note:** The service runs under user `mahmoudmajed`. If your username is different, edit `fruit-sorter.service` before installing.

---

## Project File Structure

```
grad-project/
├── main.py              # Main event loop — start here
├── config.py            # All settings: GPIO pins, sizes, AI, timing
├── camera.py            # Dual-camera capture + background threads
├── detector.py          # YOLOv8 + OpenCV fruit size measurement
├── classifier.py        # Size classification (small / medium / big)
├── relay_controller.py  # GPIO relay control with timed pulses
├── keypad.py            # 4×4 matrix keypad driver
├── oled_display.py      # I2C OLED display (idle stats + events)
├── ir_sensor.py         # IR obstacle sensor driver
├── calibrate.py         # Interactive PIXELS_PER_MM calibration
├── fruit-sorter.service # Systemd service for auto-start on boot
├── monitor/
│   └── server.py        # Live MJPEG web viewer for both cameras
├── scripts/
│   ├── install-service.sh   # One-command service installer
│   └── uninstall-service.sh # Service uninstaller
├── assets/
│   ├── PixelOperator.ttf       # OLED text font
│   └── lineawesome-webfont.ttf # OLED icon font
├── tests/
│   ├── test_classifier.py      # Classifier unit tests
│   ├── test_relay_timing.py    # Relay timing tests
│   └── test_camera_debug.py    # Camera debug tests
├── requirements.txt     # Python dependencies
├── yolov8n.pt           # YOLOv8-nano weights (~6 MB)
└── docs/
    └── SETUP.md         # ← You are here
```

---

## Quick Start Checklist

- [ ] Flash Raspberry Pi OS (64-bit Bookworm) and enable I2C + Camera
- [ ] Wire all components per the GPIO table (Section 3)
- [ ] Connect both cameras to CAM0 and CAM1 ports
- [ ] Verify cameras: `libcamera-hello --list-cameras`
- [ ] Verify OLED: `i2cdetect -y 1` → should show `0x3C`
- [ ] Clone repo and install: `python3 -m venv venv --system-site-packages && source venv/bin/activate && pip install -r requirements.txt`
- [ ] Download fonts to `assets/`
- [ ] Calibrate cameras: `python calibrate.py`
- [ ] Run: `python main.py`
- [ ] Open browser: `http://<pi-ip>:8080`
- [ ] (Optional) Enable auto-start: `sudo bash scripts/install-service.sh`
