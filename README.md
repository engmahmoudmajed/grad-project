# Fruit Classification System 🍎🍊🍋

A Raspberry Pi embedded system that automatically classifies fruit by size and activates conveyor belt sorting gates using a hybrid AI (YOLOv8) + Computer Vision (OpenCV) approach.

## Features
- **Dual Camera Vision**: Utilizes both `ov5647` and `imx219` cameras to capture the best possible frame of the moving fruit.
- **Hybrid AI Detection**: Uses YOLOv8-nano for high-confidence fruit bounding boxes, falling back to OpenCV Otsu threshold contour detection when needed.
- **Live MJPEG Monitor**: Includes a lightweight web server (`monitor/server.py`) to stream both cameras live to any browser on the network.
- **Hardware Integration**: 
  - 4x4 Keypad for selecting produce category
  - SSD1306/SH1106 OLED Display for live UI and stats
  - IR Sensor for physical trigger
  - Automated Relay control for sorting gates

## Hardware Setup

| Component | GPIO (BCM) |
|-----------|-----------|
| 4×4 Keypad Rows | 18, 23, 24, 25 |
| 4×4 Keypad Cols | 10, 22, 27, 17 |
| Relay 1–4 | 16, 20, 21, 19 |
| IR Sensor | 26 |
| OLED SDA/SCL | 2 / 3 (I2C) |

*Note: Relays are configured as active-High (Normally-Open).*

## Project Structure

```text
grad-project/
├── main.py              # Main event loop
├── config.py            # GPIO pins, produce sizes, AI & timing constants
├── camera.py            # Dual-camera capture and pipeline manager
├── detector.py          # YOLOv8 + OpenCV size measurement logic
├── classifier.py        # Size classification logic
├── relay_controller.py  # GPIO relay control with timed pulses
├── keypad.py            # 4×4 matrix keypad driver
├── oled_display.py      # I2C OLED display (idle stats + events)
├── ir_sensor.py         # IR obstacle sensor driver
├── calibrate.py         # Interative tool to compute PIXELS_PER_MM
├── monitor/             
│   └── server.py        # Live MJPEG viewer for both cameras
├── requirements.txt     # Python dependencies
├── assets/              # Font files for OLED display
└── tests/               # Unit tests (run on any machine)
```

## How it works

1. **Keypad**: Press `C` + `1–9` to select produce type (Apple=1, Orange=2, … Lemon=9).
2. **IR Sensor**: Detects a fruit passing on the conveyor belt.
3. **Camera Pipeline**: Captures images from both cameras. `detector.py` uses YOLOv8 (and OpenCV fallback) to find the best bounding box and calculates size in mm.
4. **Classifier**: Compares the measured size to the produce's known size table.
5. **Relay**: Schedules the correct sorting gate to open after a delay:
   - Small → Relay 1, after 5 s
   - Medium → Relay 2, after 10 s
   - Big → Relay 3, after 15 s
6. **OLED**: Shows live system status and flashes classification results for 3 seconds.

## Setup

> 📖 **For the complete step-by-step guide** (hardware assembly, wiring, OS setup, calibration, and troubleshooting), see **[docs/SETUP.md](docs/SETUP.md)**.
>
> 📷 **For camera mounting dimensions and layout**, see **[docs/CAMERA_PLACEMENT.md](docs/CAMERA_PLACEMENT.md)**.

```bash
# Clone the repository
git clone <repository-url>
cd grad-project

# Setup virtual environment and install dependencies
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt

# Copy font files to assets/ (see assets/README.md)
```

## Running the System

**Terminal 1: Start the automated sorter**
```bash
source venv/bin/activate
python main.py
```

**Terminal 2 (Optional): Start the Live Monitor**
```bash
source venv/bin/activate
python monitor/server.py
```
Open your browser at: `http://<raspberry-pi-ip>:8080`

**Calibration**
To calibrate the `PIXELS_PER_MM` conversion ratio for your camera height:
```bash
source venv/bin/activate
python calibrate.py
```

## Produce Size Reference

| # | Produce | Small (mm) | Medium (mm) | Big (mm) |
|---|---------|-----------|------------|----------|
| 1 | Apple | 50–65 | 65–80 | 80–95 |
| 2 | Orange | 60–70 | 70–85 | 85–100 |
| 3 | Banana | 100–130 | 130–160 | 160–190 |
| 4 | Tomato | 30–45 | 45–60 | 60–75 |
| 5 | Potato | 30–50 | 50–70 | 70–90 |
| 6 | Onion | 40–55 | 55–75 | 75–95 |
| 7 | Bell Pepper | 60–80 | 80–100 | 100–120 |
| 8 | Cucumber | 120–180 | 180–240 | 240–300 |
| 9 | Lemon | 40–50 | 50–60 | 60–70 |
