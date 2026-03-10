# Fruit Classification System 🍎🍊🍋

A Raspberry Pi 5 embedded system that automatically classifies fruit by size and activates conveyor belt sorting gates.

## Hardware

| Component | GPIO (BCM) |
|-----------|-----------|
| 4×4 Keypad Rows | 18, 23, 24, 25 |
| 4×4 Keypad Cols | 10, 22, 27, 17 |
| Relay 1–4 | 16, 20, 21, 19 |
| IR Sensor | 26 |
| OLED SDA/SCL | 2 / 3 (I2C) |

## Project Structure

```
grad-project/
├── main.py              # Main event loop
├── config.py            # GPIO pins, produce sizes, timing constants
├── camera.py            # Image capture + OpenCV size measurement
├── classifier.py        # Size classification logic
├── relay_controller.py  # GPIO relay control with timed pulses
├── keypad.py            # 4×4 matrix keypad driver
├── oled_display.py      # SH1106 OLED display (idle stats + events)
├── ir_sensor.py         # IR obstacle sensor driver
├── requirements.txt     # Python dependencies
├── assets/              # Font files for OLED display
└── tests/               # Unit tests (run on any machine)
```

## How it works

1. **Keypad**: Press `C` + `1–9` to select produce type (Apple=1, Orange=2, … Lemon=9)
2. **IR Sensor**: Detects a fruit passing on the conveyor belt
3. **Camera**: Captures an image and measures the fruit's size in mm using OpenCV
4. **Classifier**: Compares the measured size to the produce's known size table
5. **Relay**: Schedules the correct sorting gate to open after a delay:
   - Small → Relay 1, after 5 s
   - Medium → Relay 2, after 10 s
   - Big → Relay 3, after 15 s
6. **OLED**: Shows live system status and flashes classification results for 3 seconds

## Setup

```bash
# On the Raspberry Pi
pip install -r requirements.txt

# Copy font files to assets/ (see assets/README.md)

# Calibrate the camera (measure a known object, update PIXELS_PER_MM in config.py)

# Run
python main.py
```

## Running Tests (on any machine)

```bash
pip install pytest
python -m pytest tests/ -v
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
