import subprocess
import threading
import re
import time
from datetime import datetime
import xml.etree.ElementTree as ET
import os

def get_connected_devices():
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    devices = []
    for line in lines[1:]:
        if line.strip():
            parts = line.split('\t')
            if len(parts) == 2 and parts[1] == 'device':
                devices.append(parts[0])
    return devices

def choose_device(devices):
    print("Multiple devices connected:")
    for idx, device in enumerate(devices):
        print(f"{idx + 1}. {device}")
    while True:
        try:
            choice = int(input("Select the device number to use: "))
            if 1 <= choice <= len(devices):
                return devices[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(devices)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def start_browser_and_download(download_url, package_name, activity_name, device_id):
    adb_command = ['adb', 'shell', 'am', 'start', '-n', f'{package_name}/{activity_name}',
                   '-a', 'android.intent.action.VIEW', '-d', download_url]
    if device_id:
        adb_command.insert(1, '-s')
        adb_command.insert(2, device_id)
    subprocess.run(adb_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)

def dump_ui_hierarchy(device_id):
    if os.path.exists('ui_dump.xml'):
        os.remove('ui_dump.xml')
    adb_command_dump = ['adb', 'shell', 'uiautomator', 'dump', '/sdcard/ui_dump.xml']
    adb_command_pull = ['adb', 'pull', '/sdcard/ui_dump.xml']
    if device_id:
        adb_command_dump.insert(1, '-s')
        adb_command_dump.insert(2, device_id)
        adb_command_pull.insert(1, '-s')
        adb_command_pull.insert(2, device_id)
    subprocess.run(adb_command_dump, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(adb_command_pull, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def find_element_bounds(xml_file, text=None, resource_id=None, content_desc=None, class_name=None):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    for node in root.iter('node'):
        node_text = node.attrib.get('text')
        node_resource_id = node.attrib.get('resource-id')
        node_content_desc = node.attrib.get('content-desc')
        node_class = node.attrib.get('class')
        if resource_id and node_resource_id and resource_id == node_resource_id:
            bounds = node.attrib.get('bounds')
            return bounds
        if text and node_text and text.lower() in node_text.lower():
            if class_name and node_class != class_name:
                continue
            bounds = node.attrib.get('bounds')
            return bounds
        if content_desc and node_content_desc and content_desc.lower() in node_content_desc.lower():
            bounds = node.attrib.get('bounds')
            return bounds
    return None

def get_center_coordinates(bounds):
    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
    if match:
        left, top, right, bottom = map(int, match.groups())
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        return center_x, center_y
    else:
        return None

def tap_screen(x, y, device_id):
    adb_command = ['adb', 'shell', 'input', 'tap', str(x), str(y)]
    if device_id:
        adb_command.insert(1, '-s')
        adb_command.insert(2, device_id)
    subprocess.run(adb_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def click_download_button(device_id):
    max_attempts = 5
    for attempt in range(max_attempts):
        dump_ui_hierarchy(device_id)
        bounds = find_element_bounds('ui_dump.xml', resource_id='org.mozilla.firefox:id/positive_button')
        if not bounds:
            bounds = find_element_bounds('ui_dump.xml', resource_id='android:id/button1')
        if not bounds:
            bounds = find_element_bounds('ui_dump.xml', text='Download', class_name='android.widget.Button')
        if not bounds:
            bounds = find_element_bounds('ui_dump.xml', text='Download')
        if bounds:
            coordinates = get_center_coordinates(bounds)
            if coordinates:
                x, y = coordinates
                tap_screen(x, y, device_id)
                print(f"Tapped on Download button at ({x}, {y}).")
                return True
        else:
            print(f"Download button not found. Attempt {attempt + 1}/{max_attempts}")
            time.sleep(2)
    print("Failed to find and tap the download button after multiple attempts.")
    return False

def parse_log_time(log_line):
    match = re.match(r'^(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})', log_line)
    if match:
        timestamp_str = match.group(1)
        current_year = datetime.now().year
        timestamp_str_with_year = f"{current_year}-{timestamp_str}"
        try:
            timestamp = datetime.strptime(timestamp_str_with_year, '%Y-%m-%d %H:%M:%S.%f')
            return timestamp
        except ValueError as e:
            print(f"Failed to parse timestamp '{timestamp_str_with_year}': {e}")
            return None
    else:
        print(f"No timestamp found in log line: {log_line}")
        return None

def monitor_adb_logs(start_event, end_event, result_dict, device_id):
    adb_command = ['adb', 'logcat', '-v', 'time']
    if device_id:
        adb_command.insert(1, '-s')
        adb_command.insert(2, device_id)
    process = subprocess.Popen(adb_command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               universal_newlines=True,
                               bufsize=1)
    start_pattern = re.compile(r'Open with FUSE\. FilePath: .*\.pending-.*')
    end_pattern = re.compile(r'Moving /storage/emulated/0/Download/\.pending-.* to /storage/emulated/0/Download/.*')
    for line in process.stdout:
        line = line.strip()
        if start_pattern.search(line):
            print(f"Download started: {line}")
            timestamp = parse_log_time(line)
            if timestamp:
                result_dict['start_time'] = timestamp
                start_event.set()
        elif end_pattern.search(line):
            print(f"Download finished: {line}")
            timestamp = parse_log_time(line)
            if timestamp:
                result_dict['end_time'] = timestamp
                end_event.set()
                break
    process.terminate()

def calculate_download_duration(start_time, end_time):
    duration = (end_time - start_time).total_seconds()
    return duration

def clear_adb_logs(device_id):
    adb_command = ['adb', 'logcat', '-c']
    if device_id:
        adb_command.insert(1, '-s')
        adb_command.insert(2, device_id)
    subprocess.run(adb_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def close_browser(package_name, device_id):
    adb_command = ['adb', 'shell', 'am', 'force-stop', package_name]
    if device_id:
        adb_command.insert(1, '-s')
        adb_command.insert(2, device_id)
    subprocess.run(adb_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_profiling(package_name, device_id, profiling_duration, ndk_path):
    import threading

    print("Starting profiling with simpleperf...")
    app_profiler_path = os.path.join(ndk_path, 'simpleperf', 'app_profiler.py')
    profiling_cmd = [
        app_profiler_path,
        '-p', package_name,
        '-r', "-g --duration 200 -f 1000 --trace-offcpu -e cpu-clock:u"
    ]

    profiling_process = subprocess.Popen(
        profiling_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )


    def read_output(pipe):
        for line in iter(pipe.readline, ''):
            print(line, end='')
        pipe.close()

    threading.Thread(target=read_output, args=(profiling_process.stdout,), daemon=True).start()
    threading.Thread(target=read_output, args=(profiling_process.stderr,), daemon=True).start()

    return profiling_process


def stop_profiling(profiling_process):
    print("Stopping profiling...")
    profiling_process.wait()
    print("Profiling stopped.")

def test_download_speed(download_url, browser_info, device_id, profiling_enabled=False, ndk_path=None):
    start_event = threading.Event()
    end_event = threading.Event()
    result_dict = {}

    if profiling_enabled:
        profiling_duration = 200
        profiling_process = start_profiling(browser_info['package_name'], device_id, profiling_duration, ndk_path)
        if profiling_process is None:
            print("Exiting due to profiling start failure.")
            return None

    clear_adb_logs(device_id)

    log_thread = threading.Thread(target=monitor_adb_logs,
                                  args=(start_event, end_event, result_dict, device_id))
    log_thread.start()

    start_browser_and_download(download_url, browser_info['package_name'], browser_info['activity_name'], device_id)

    time.sleep(5)

    if not click_download_button(device_id):
        print("Failed to initiate download.")
        log_thread.join()
        if profiling_enabled:
            stop_profiling(profiling_process)
        return None

    print("Waiting for download to start...")
    if not start_event.wait(timeout=60):
        print("Download did not start within 60 seconds.")
        log_thread.join()
        if profiling_enabled:
            stop_profiling(profiling_process)
        return None

    print("Waiting for download to complete...")
    if not end_event.wait(timeout=900):
        print("Download did not finish within 15 minutes.")
        log_thread.join()
        if profiling_enabled:
            stop_profiling(profiling_process)
        return None

    start_time = result_dict.get('start_time')
    end_time = result_dict.get('end_time')

    close_browser(browser_info['package_name'], device_id)

    if profiling_enabled:
        stop_profiling(profiling_process)

    if start_time and end_time:
        duration = calculate_download_duration(start_time, end_time)
        print(f"Download completed in {duration} seconds.")
    else:
        print("Could not determine download times.")
        duration = None

    log_thread.join()
    return duration

def main():
    #download_url = 'https://link.testfile.org/300MB
    # download_url = 'https://link.testfile.org/500MB'
    # download_url = 'https://testfile.org/1.3GBiconpng'
    # download_url = 'https://testfile.org/file-kali-3.9GB-2'
    download_url = 'https://testfile.org/files-5GB-zip'

    browsers = {
        '1': {
            'name': 'Firefox',
            'package_name': 'org.mozilla.firefox',
            'activity_name': 'org.mozilla.gecko.BrowserApp',
        },
        '2': {
            'name': 'Chrome',
            'package_name': 'com.android.chrome',
            'activity_name': 'com.google.android.apps.chrome.Main',
        }
    }

    devices = get_connected_devices()
    if not devices:
        print("No devices connected. Please connect an Android device and try again.")
        exit(1)
    elif len(devices) == 1:
        device_id = devices[0]
        print(f"Using device: {device_id}")

        profiling_enabled = input("Do you want to enable profiling during the download? (yes/no): ").lower() == 'yes'
        ndk_path = None
        if profiling_enabled:
            ndk_path = input("Please enter the path to your android-ndk directory within mozbuild (e.g., ~/.mozbuild/android-ndk-r27b): ")
            while not os.path.isdir(ndk_path):
                print("Invalid path. Please try again.")
                ndk_path = input("Please enter the path to your android-ndk directory within mozbuild (e.g., ~/.mozbuild/android-ndk-r27b): ")
    else:
        print("Multiple devices connected:")
        for idx, device in enumerate(devices):
            print(f"{idx + 1}. {device}")
        while True:
            try:
                choice = int(input("Select the device number to use: "))
                if 1 <= choice <= len(devices):
                    device_id = devices[choice - 1]
                    print(f"Using device: {device_id}")
                    break
                else:
                    print(f"Please enter a number between 1 and {len(devices)}.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        profiling_enabled = False
        ndk_path = None
        print("Profiling is disabled when multiple devices are connected.")

    compare_speeds = input("Do you want to compare download speeds between two browsers? (yes/no): ").lower() == 'yes'

    durations = {}

    if compare_speeds:
        for key in ['1', '2']:
            browser_info = browsers[key]
            print(f"\nTesting download speed with {browser_info['name']} on device {device_id}...")
            duration = test_download_speed(download_url, browser_info, device_id, profiling_enabled, ndk_path)
            if duration is not None:
                print(f"Download with {browser_info['name']} completed in {duration} seconds.")
                durations[browser_info['name']] = duration
            else:
                print(f"Download test with {browser_info['name']} failed.")
    else:
        print("Select a browser to test:")
        for key, browser in browsers.items():
            print(f"{key}. {browser['name']}")
        browser_choice = input("Enter the number of the browser: ")
        while browser_choice not in browsers:
            print("Invalid choice. Please try again.")
            browser_choice = input("Enter the number of the browser: ")
        browser_info = browsers[browser_choice]
        print(f"\nTesting download speed with {browser_info['name']} on device {device_id}...")
        duration = test_download_speed(download_url, browser_info, device_id, profiling_enabled, ndk_path)
        if duration is not None:
            print(f"Download completed in {duration} seconds.")
            durations[browser_info['name']] = duration
        else:
            print("\nDownload test failed.")

    if compare_speeds and len(durations) == 2:
        print("\nDownload speed comparison:")
        for browser_name, duration in durations.items():
            print(f"{browser_name}: {duration} seconds")
        diff = abs(durations['Firefox'] - durations['Chrome'])
        if durations['Firefox'] < durations['Chrome']:
            faster_browser = 'Firefox'
        elif durations['Chrome'] < durations['Firefox']:
            faster_browser = 'Chrome'
        else:
            faster_browser = None
            print("\nBoth browsers had the same download duration.")
        if faster_browser:
            print(f"\n{faster_browser} was faster by {diff} seconds.")
    elif len(durations) == 1:
        browser_name = list(durations.keys())[0]
        print(f"\nDownload with {browser_name} completed in {durations[browser_name]} seconds.")

    if profiling_enabled:
        print("\nTo view the profiling data, run the following command:")
        print("samply import perf.data --breakpad-symbol-server https://symbols.mozilla.org/")

if __name__ == "__main__":
    main()
