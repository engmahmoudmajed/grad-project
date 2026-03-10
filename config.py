"""
config.py – Central configuration for the Fruit Classification System.
All GPIO pins, produce size tables, and timing constants live here.
"""

# ─── GPIO Pins (BCM numbering) ───────────────────────────────────────────────

# 4×4 Matrix Keypad
KEYPAD_ROWS = [18, 23, 24, 25]   # Output (driven HIGH one at a time)
KEYPAD_COLS = [10, 22, 27, 17]   # Input  (read to detect which column is pressed)

# Relay Module  (active-LOW: GPIO LOW = relay ON)
RELAY_PINS = [16, 20, 21, 19]    # Relay 1, 2, 3, 4
RELAY_ACTIVE_LOW = True          # Set False if your relay board is active-HIGH

# IR Obstacle Sensor (LOW when object detected)
IR_SENSOR_PIN = 26

# ─── Conveyor Belt Timing ─────────────────────────────────────────────────────
# Seconds AFTER the IR trigger before the relay fires
RELAY_DELAYS = {
    "small":  5,   # seconds
    "medium": 10,
    "big":    15,
}
RELAY_PULSE_DURATION = 5  # seconds – how long the relay stays ON

# ─── Relay assignment per size ────────────────────────────────────────────────
# Relay index (0-based) that handles each size category
SIZE_TO_RELAY = {
    "small":  0,   # GPIO 16 → Relay 1
    "medium": 1,   # GPIO 20 → Relay 2
    "big":    2,   # GPIO 21 → Relay 3
    # Relay 4 (GPIO 19) reserved for future use / reject lane
}

# ─── Produce Size Table ───────────────────────────────────────────────────────
# Format: [[small_min, small_max], [medium_min, medium_max], [big_min, big_max]] in mm
# Index:   0=Apple  1=Orange  2=Banana  3=Tomato  4=Potato
#          5=Onion  6=Bell Pepper  7=Cucumber  8=Lemon

PRODUCE_NAMES = [
    "Apple",       # 0
    "Orange",      # 1
    "Banana",      # 2
    "Tomato",      # 3
    "Potato",      # 4
    "Onion",       # 5
    "Bell Pepper", # 6
    "Cucumber",    # 7
    "Lemon",       # 8
]

PRODUCE_SIZES_MM = [
    # [small],       [medium],      [big]
    [[50,  65],  [65,  80],  [80,  95]],   # Apple (diameter)
    [[60,  70],  [70,  85],  [85, 100]],   # Orange (diameter)
    [[100, 130], [130, 160], [160, 190]],  # Banana (length)
    [[30,  45],  [45,  60],  [60,  75]],   # Tomato (diameter)
    [[30,  50],  [50,  70],  [70,  90]],   # Potato (diameter)
    [[40,  55],  [55,  75],  [75,  95]],   # Onion (diameter)
    [[60,  80],  [80, 100],  [100, 120]],  # Bell Pepper (height)
    [[120, 180], [180, 240], [240, 300]],  # Cucumber (length)
    [[40,  50],  [50,  60],  [60,  70]],   # Lemon (diameter)
]

# ─── Camera / Size Measurement ────────────────────────────────────────────────
CAPTURE_PATH      = "/tmp/fruit_capture.jpg"
# Calibration: how many pixels correspond to 1 mm at the camera's working distance.
# Measure a known-size object to calibrate this value.
PIXELS_PER_MM     = 5.0   # ← UPDATE after hardware calibration

# ─── OLED Display ─────────────────────────────────────────────────────────────
OLED_I2C_PORT    = 1
OLED_I2C_ADDRESS = 0x3C
OLED_WIDTH       = 128
OLED_HEIGHT      = 64
OLED_EVENT_SECS  = 3      # seconds to show an event message before returning to idle

# ─── Keypad Layout ────────────────────────────────────────────────────────────
KEYPAD_LAYOUT = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]

# ─── IR Sensor ────────────────────────────────────────────────────────────────
IR_DEBOUNCE_SECS = 1.0   # ignore re-triggers within this window
