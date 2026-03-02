# CLASSFICATION FRUIT PROJECT

How our project work

conveyor belt work on specidfc speed
our project in top of it

---

## steps for How Project work

1. App Take image of the fruit and save size
2. after ir send signal the fruit pass
    if fruitSize == small
    after 5 second
    send to realy 1 and work for 5s
    if fruitSize == medium
    after 10 second
    send to realy 2 and work for 5s
    if fruitSize == big
    after 15 second
    send to realy 3 and work for 5s
    else
    dont send any signal for any relay

3.what keypad do




4.What oled show
  1.alawys show next

  ```py
  import os
  import time
  import subprocess
  from PIL import Image, ImageDraw, ImageFont
  from luma.core.interface.serial import i2c
  from luma.oled.device import sh1106

  # --- Configuration ---
  WIDTH = 128
  HEIGHT = 64
  LOOPTIME = 1.0

  # Initialize I2C and SH1106 Device
  # Address is usually 0x3C. If it stays black, try changing to 0x3D.
  serial = i2c(port=1, address=0x3C)
  device = sh1106(serial, width=WIDTH, height=HEIGHT, rotate=0)

  # Create a blank image for drawing
  # '1' means 1-bit color (black and white)
  image = Image.new('1', (device.width, device.height))
  draw = ImageDraw.Draw(image)

  # --- Fonts ---
  # DETERMINE THE PATH TO THE CURRENT SCRIPT
  # This ensures Python looks for fonts in the same folder as the script,
  # no matter where you run it from.
  basedir = os.path.dirname(os.path.realpath(__file__))
  font_path_1 = os.path.join(basedir, 'PixelOperator.ttf')
  font_path_2 = os.path.join(basedir, 'lineawesome-webfont.ttf')

  # --- Fonts ---
  try:
    font = ImageFont.truetype(font_path_1, 16)
    icon_font = ImageFont.truetype(font_path_2, 18)
  except IOError as e:
    print(f"Error loading fonts: {e}")
    print("Trying to load from:", font_path_1)
    print("Falling back to default font (No Icons).")
    font = ImageFont.load_default()
    icon_font = ImageFont.load_default()

  # --- Layout ---
  padding = -2
  top = padding
  x = 0

  while True:
    # Clear the image (fill with black)
    draw.rectangle((0, 0, device.width, device.height), outline=0, fill=0)

    # 1. IP Address
    cmd = "hostname -I | cut -d\' \' -f1 | head --bytes -1"
    try:
        IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
    except:
        IP = "No IP"

    # 2. CPU Load
    cmd = "top -bn1 | grep load | awk '{printf \"%.2fLA\", $(NF-2)}'"
    try:
        CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
    except:
        CPU = "0.00"

    # 3. Memory Usage
    cmd = "free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'"
    try:
        MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
    except:
        MemUsage = "0%"

    # 4. Disk Usage
    cmd = "df -h | awk '$NF==\"/\"{printf \"%d/%dGB\", $3,$2}'"
    try:
        Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")
    except:
        Disk = "0/0GB"

    # 5. Temperature
    cmd = "cat /sys/class/thermal/thermal_zone*/temp | awk -v CONVFMT='%.1f' '{printf $1/1000}'"
    try:
        Temperature = subprocess.check_output(cmd, shell=True).decode("utf-8")
    except:
        Temperature = "0"

    # --- Draw Icons (LineAwesome glyphs) ---
    # These chr() codes correspond to specific icons in the font file
    draw.text((x, top + 5), chr(62609), font=icon_font, fill=255)       # Thermometer
    draw.text((x + 65, top + 5), chr(62776), font=icon_font, fill=255)  # Memory Chip
    draw.text((x, top + 25), chr(63426), font=icon_font, fill=255)      # HDD
    draw.text((x + 65, top + 25), chr(62171), font=icon_font, fill=255) # CPU Chip
    draw.text((x, top + 45), chr(61931), font=icon_font, fill=255)      # Wifi

    # --- Draw Text ---
    # \u00B0 is the safe way to write the degree symbol
    draw.text((x + 19, top + 5), f"{Temperature}\u00B0C", font=font, fill=255)
    draw.text((x + 87, top + 5), MemUsage, font=font, fill=255)
    draw.text((x + 19, top + 25), Disk, font=font, fill=255)
    draw.text((x + 87, top + 25), CPU, font=font, fill=255)
    draw.text((x + 19, top + 45), IP, font=font, fill=255)

    # Send the image to the screen
    device.display(image)

    time.sleep(LOOPTIME)

  ```
  2. but if one click 

