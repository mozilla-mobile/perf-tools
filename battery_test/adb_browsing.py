import subprocess
import time

PACKAGE = "com.android.chrome"
ACTIVITY = "com.google.android.apps.chrome.Main"
XML_FILE = "window_dump.xml"

# Test URLs
URLS = [
    "https://facebook.com/",
    "https://instagram.com",
    "https://instagram.com/explore/",
    "https://buzzfeed.com",
    "https://cnn.com",
    "https://tmz.com",
    "https://perezhilton.com",
    "https://wikipedia.org/wiki/Student%27s_t-test",
    "https://searchfox.org/mozilla-central/source/toolkit/components/telemetry/Histograms.json",
]

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def extract_bounds(xml_file, resource_id):
    cmd = f"xmllint --xpath \"string(//node[@resource-id='{resource_id}']/@bounds)\" {xml_file}"
    result = run_cmd(cmd)
    bounds = result.stdout.strip()
    if not bounds:
        raise ValueError(f"Could not find bounds for resource-id {resource_id}")

    try:
        left, top = map(int, bounds.split('][')[0][1:].split(','))
        right, bottom = map(int, bounds.split('][')[1][:-1].split(','))
    except ValueError:
        raise ValueError(f"Failed to parse bounds '{bounds}' for resource-id {resource_id}")

    x = (left + right) // 2
    y = (top + bottom) // 2
    return x, y


def tap(x, y):
    run_cmd(f"adb -s R5CTB1NTHSF shellinput tap {x} {y}")
    time.sleep(2)

def input_text(text):
    for character in text:
        run_cmd(f"adb -s R5CTB1NTHSF shellinput text '{character}'")
    time.sleep(2)

def scroll_down():
    run_cmd("adb -s R5CTB1NTHSF shellinput swipe 500 1500 500 300 500")
    time.sleep(3)

def scroll_up():
    run_cmd("adb -s R5CTB1NTHSF shellinput swipe 500 300 500 1500 500")
    time.sleep(3)

def start_browser(url):
    run_cmd(f"adb -s R5CTB1NTHSF shellam start -n {PACKAGE}/{ACTIVITY} -d {url}")
    time.sleep(4)

def close_browser():
    run_cmd(f"adb -s R5CTB1NTHSF shellam force-stop {PACKAGE}")

def setup():
    run_cmd("adb -s R5CTB1NTHSF shelluiautomator dump /sdcard/window_dump.xml")
    run_cmd("adb -s R5CTB1NTHSF pull /sdcard/window_dump.xml")

def browse_url(url):
    start_browser(url)
    setup()
    toolbar_x, toolbar_y = extract_bounds(XML_FILE, 'com.android.chrome:id/search_box_text')
    tap(toolbar_x, toolbar_y)
    input_text(url)
    run_cmd("adb -s R5CTB1NTHSF shellinput keyevent 66")  # KEYCODE_ENTER
    time.sleep(10)
    scroll_down()
    scroll_up()

def main():
    for url in URLS:
        browse_url(url)
    close_browser()

if __name__ == "__main__":
    main()
