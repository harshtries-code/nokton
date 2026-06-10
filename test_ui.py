import pygetwindow as gw
import pyautogui
import time
import mss
from PIL import Image

time.sleep(5)

# Find Nokton
for attempt in range(10):
    wins = [w for w in gw.getAllWindows() if w.title == 'Nokton']
    if wins:
        break
    time.sleep(2)

if not wins:
    print("Nokton not found after 20s")
    exit(1)

w = wins[0]
time.sleep(1)
try:
    w.activate()
except Exception:
    pass
time.sleep(1)

# Screenshot initial state
sct = mss.MSS()
region = {'top': max(0, w.top), 'left': max(0, w.left), 'width': w.width, 'height': w.height}
img = sct.grab(region)
pil_img = Image.frombytes('RGB', img.size, img.bgra, 'raw', 'BGRX')
pil_img.save('screenshot_v2_initial.png')
print('Saved initial')

# Type in input
inputY = w.top + w.height - 30
inputX = w.left + 400
pyautogui.click(inputX, inputY)
time.sleep(0.3)
pyautogui.typewrite('hi, tell me what you can do in one sentence', interval=0.02)
time.sleep(0.2)
pyautogui.press('enter')
time.sleep(10)

# Screenshot response
img2 = sct.grab(region)
pil_img2 = Image.frombytes('RGB', img2.size, img2.bgra, 'raw', 'BGRX')
pil_img2.save('screenshot_v2_response.png')
print('Saved response')

# Now test Settings button
settingsX = w.left + 510  # Settings button in control bar
settingsY = w.top + w.height - 65
pyautogui.click(settingsX, settingsY)
time.sleep(2)

img3 = sct.grab(region)
pil_img3 = Image.frombytes('RGB', img3.size, img3.bgra, 'raw', 'BGRX')
pil_img3.save('screenshot_v2_settings.png')
print('Saved settings')
