import network
import urequests
import ujson
import neopixel
import machine
import time
import random
import gc
import secrets

np = neopixel.NeoPixel(machine.Pin(secrets.LED_PIN), secrets.NUM_LEDS)


def fill(r, g, b):
    factor = secrets.BRIGHTNESS / 255.0
    colour = (int(r * factor), int(g * factor), int(b * factor))
    for i in range(secrets.NUM_LEDS):
        np[i] = colour
    np.write()


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    wlan.connect(secrets.SSID, secrets.PASSWORD)
    pos = 0
    for _ in range(300):  # 300 × 0.07 s = 21 s timeout
        if wlan.isconnected():
            return True
        for i in range(secrets.NUM_LEDS):
            np[i] = (0, 0, 0)
        np[pos % secrets.NUM_LEDS] = (0, 0, secrets.BRIGHTNESS)
        np.write()
        pos += 1
        time.sleep(0.07)
    return False


def fetch_weather():
    url = (
        'https://api.open-meteo.com/v1/forecast'
        '?latitude={}&longitude={}'
        '&daily=temperature_2m_max,precipitation_sum,snowfall_sum'
        '&past_days=1&forecast_days=1'
        '&timezone={}'
    ).format(secrets.LATITUDE, secrets.LONGITUDE, secrets.TIMEZONE)

    resp = urequests.get(url, timeout=20)
    data = ujson.loads(resp.text)
    resp.close()
    gc.collect()

    highs  = data['daily']['temperature_2m_max']
    precip = data['daily']['precipitation_sum']
    snow   = data['daily']['snowfall_sum']
    return highs[1], highs[0], precip[1], snow[1]
    # today_high, yest_high, precip_mm, snow_cm


def animate(today_high, yest_high, precip_mm, snow_cm, duration_s):
    if today_high > yest_high:
        base = (255, 80, 0)    # orange: warmer
    elif today_high < yest_high:
        base = (0, 0, 255)     # blue: colder
    else:
        base = (0, 255, 100)   # teal: same

    factor = secrets.BRIGHTNESS / 255.0
    scaled = (int(base[0] * factor), int(base[1] * factor), int(base[2] * factor))

    is_rain = precip_mm is not None and precip_mm > 1.0
    is_snow = snow_cm  is not None and snow_cm  > 0.5

    deadline = time.time() + duration_s
    while time.time() < deadline:
        if is_snow:
            fill(*base)
            px = random.randint(0, secrets.NUM_LEDS - 1)
            np[px] = (secrets.BRIGHTNESS, secrets.BRIGHTNESS, secrets.BRIGHTNESS)  # white
            np.write()
            time.sleep(0.1)
            np[px] = scaled
            np.write()
            time.sleep(0.3)
        elif is_rain:
            fill(*base)
            px = random.randint(0, secrets.NUM_LEDS - 1)
            np[px] = (0, 0, secrets.BRIGHTNESS)  # blue
            np.write()
            time.sleep(0.08)
            np[px] = scaled
            np.write()
            time.sleep(0.12)
        else:
            fill(*base)
            time.sleep(1)


def flash_green():
    for _ in range(3):
        fill(0, 255, 0)
        time.sleep(0.15)
        fill(0, 0, 0)
        time.sleep(0.15)


def main():
    if not connect_wifi():
        fill(255, 0, 128)  # pink: WiFi failed
        return

    flash_green()

    import updater
    updater.check(fill)

    while True:
        try:
            today_high, yest_high, precip_mm, snow_cm = fetch_weather()
            print('Today: {}C  Yesterday: {}C  Precip: {}mm  Snow: {}cm'.format(
                today_high, yest_high, precip_mm, snow_cm))
            animate(today_high, yest_high, precip_mm, snow_cm, 600)

        except Exception as e:
            print('Error:', e)
            fill(255, 255, 0)  # yellow: fetch or parse failure
            time.sleep(600)


main()
