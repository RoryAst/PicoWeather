import network
import urequests
import ujson
import neopixel
import machine
import time
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


def fetch_temps():
    url = (
        'https://api.open-meteo.com/v1/forecast'
        '?latitude={}&longitude={}'
        '&daily=temperature_2m_max'
        '&past_days=1&forecast_days=1'
        '&timezone={}'
    ).format(secrets.LATITUDE, secrets.LONGITUDE, secrets.TIMEZONE)

    resp = urequests.get(url, timeout=20)
    data = ujson.loads(resp.text)
    resp.close()
    gc.collect()

    highs = data['daily']['temperature_2m_max']
    return highs[1], highs[0]  # today's forecast high, yesterday's high


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
            today_high, yest_high = fetch_temps()
            print('Today high: {}C  Yesterday high: {}C'.format(today_high, yest_high))

            if today_high > yest_high:
                fill(255, 80, 0)   # orange: warmer than yesterday
            elif today_high < yest_high:
                fill(0, 0, 255)    # blue: colder than yesterday
            else:
                fill(0, 255, 100)  # teal: same as yesterday

        except Exception as e:
            print('Error:', e)
            fill(255, 255, 0)      # yellow: fetch or parse failure

        time.sleep(600)


main()
