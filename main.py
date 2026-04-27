import network
import urequests
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
    for _ in range(20):
        if wlan.isconnected():
            return True
        time.sleep(1)
    return False


def parse_temp(section, class_attr=None):
    """Find the first <temperature> in section, optionally matching class="class_attr"."""
    offset = 0
    while True:
        idx = section.find('<temperature', offset)
        if idx == -1:
            return None
        tag_end = section.find('>', idx)
        if tag_end == -1:
            return None
        val_start = tag_end + 1
        val_end = section.find('<', val_start)
        if val_end == -1:
            return None
        tag = section[idx:tag_end + 1]
        if class_attr is not None and ('class="' + class_attr + '"') not in tag:
            offset = val_end
            continue
        val = section[val_start:val_end].strip()
        if val not in ('', 'N/A', 'M', '--'):
            try:
                return float(val)
            except ValueError:
                pass
        offset = val_end


def fetch_temps():
    url = 'https://dd.weather.gc.ca/citypage_weather/xml/{}/{}_e.xml'.format(
        secrets.PROVINCE, secrets.STATION
    )
    resp = urequests.get(url, timeout=20)
    xml = resp.text
    resp.close()

    c0 = xml.find('<currentConditions>')
    c1 = xml.find('</currentConditions>', c0)
    current = parse_temp(xml[c0:c1])

    y0 = xml.find('<yesterdayConditions>')
    y1 = xml.find('</yesterdayConditions>', y0)
    yest_high = parse_temp(xml[y0:y1], 'high')

    xml = None  # free before GC
    gc.collect()

    return current, yest_high


def main():
    fill(20, 20, 20)  # dim white: connecting to WiFi

    if not connect_wifi():
        fill(255, 0, 128)  # pink: WiFi failed — fix credentials and reset
        return

    import updater
    updater.check()
    # If an update was found, machine.reset() was called above and we never reach here.

    while True:
        try:
            current, yest_high = fetch_temps()
            print('Now: {}C  Yesterday high: {}C'.format(current, yest_high))

            if current is None or yest_high is None:
                fill(255, 165, 0)  # amber: data missing from feed
            elif current > yest_high:
                fill(255, 0, 0)    # red: warmer than yesterday
            elif current < yest_high:
                fill(0, 0, 255)    # blue: colder than yesterday
            else:
                fill(0, 255, 100)  # teal: same as yesterday

        except Exception as e:
            print('Error:', e)
            fill(255, 255, 0)      # yellow: network or parse failure

        time.sleep(600)  # refresh every 10 minutes


main()
