
import time
import pygame
import numpy as np
import spidev
from gpiozero import DigitalOutputDevice, Button
from picamera2 import Picamera2
from datetime import datetime
WIDTH = 480
HEIGHT = 320
import os
PHOTO_DIR = "/home/stewers/photos"
os.makedirs(PHOTO_DIR, exist_ok=True)
DC = DigitalOutputDevice(24)   # physical pin 18
RST = DigitalOutputDevice(25)  # physical pin 22
SHUTTER = Button(17, pull_up=True, bounce_time=0.08)
last_capture = 0

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 8000000
spi.mode = 0

def cmd(c):
    DC.off()
    spi.xfer2([c])

def data(values):
    DC.on()
    for i in range(0, len(values), 4096):
        spi.xfer2(values[i:i + 4096])

def reset():
    RST.on()
    time.sleep(0.05)
    RST.off()
    time.sleep(0.05)
    RST.on()
    time.sleep(0.15)

def init_tft():
    reset()
    cmd(0x01)
    time.sleep(0.15)
    cmd(0x11)
    time.sleep(0.15)
    cmd(0x3A)
    data([0x66])  # ILI9488 RGB666 / 18-bit
    cmd(0x36)
    data([0x28])
    cmd(0x29)
    time.sleep(0.05)

def window(x0, y0, x1, y1):
    cmd(0x2A)
    data([x0 >> 8, x0 & 255, x1 >> 8, x1 & 255])
    cmd(0x2B)
    data([y0 >> 8, y0 & 255, y1 >> 8, y1 & 255])
    cmd(0x2C)

def surface_to_tft(surface):
    rgb = pygame.image.tostring(surface, "RGB")
    window(0, 0, WIDTH - 1, HEIGHT - 1)
    DC.on()
    for i in range(0, len(rgb), 4096):        spi.xfer2(list(rgb[i:i + 4096]))

init_tft()
pygame.init()

display = pygame.Surface((WIDTH, HEIGHT))
font = pygame.font.SysFont(None, 26)

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
))
picam2.start()
time.sleep(1)

def push_frame():
    surface_to_tft(display)

def take_photo_with_preview():
    filename = datetime.now().strftime("photo_%Y%m%d_%H%M%S.jpg")
    path = os.path.join(PHOTO_DIR, filename)
    steps = 2
    # freeze current preview frame
    frozen = display.copy()

    # capture while shutter is closed
    picam2.capture_file(path)
    print(f"Saved {path}")

    # shutter open animation into captured image
    img = pygame.image.load(path)
    img = pygame.transform.scale(img, (WIDTH, HEIGHT))

    for i in range(steps, -1, -1):
        display.blit(img, (0, 0))
        h = int((HEIGHT / 2) * (i / steps))
        pygame.draw.rect(display, (0, 0, 0), (0, 0, WIDTH, h))
        pygame.draw.rect(display, (0, 0, 0), (0, HEIGHT - h, WIDTH, h))
        surface_to_tft(display)
        time.sleep(0.0028)

    # photo review with a little border pulse
#    for thickness in [2, 4, 6, 4, 2]:
 #       display.blit(img, (0, 0))
  #      pygame.draw.rect(display, (255, 255, 255), (4, 4, WIDTH - 8, HEIGHT - 8), thickness)
   #     surface_to_tft(display)
    #    time.sleep(0.08)

    time.sleep(1.4)
    return path
while True:
    frame = picam2.capture_array()
    frame = frame[:, :, [2, 1, 0]]

    cam_surface = pygame.surfarray.make_surface(np.rot90(frame))
    cam_surface = pygame.transform.scale(cam_surface, (WIDTH, HEIGHT))

    display.blit(cam_surface, (0, 0))

   # pygame.draw.rect(display, (0, 0, 0), (0, 0, WIDTH, 34))

    rec = font.render("PHOTO", True, (255, 60, 60))
    display.blit(rec, (12, 8))

    label = font.render("CAM  LIVE", True, (0, 255, 80))
    display.blit(label, (70, 8))

    pygame.draw.circle(display, (255, 0, 0), (WIDTH - 22, 17), 7)

    pygame.draw.line(display, (0, 255, 80), (220, 160), (260, 160), 1)
    pygame.draw.line(display, (0, 255, 80), (240, 140), (240, 180), 1)

    if SHUTTER.is_pressed:
         take_photo_with_preview()
         time.sleep(0.3)
    surface_to_tft(display)
