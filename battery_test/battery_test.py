import subprocess
import time
import datetime
import os
import sys
import re
import argparse
import threading
import queue
import signal


def run_adb_command(command, serialID=None):
    if serialID is None:
        print(command)
        return subprocess.check_output(["adb", "shell"] + command.split(), text=True)
    return subprocess.check_output(["adb", "-s", serialID, "shell"] + command.split(), text=True)


def start_app(package, activity, serialID=None):
    run_adb_command(f"am start -n {package}/{activity}", serialID)


def start_browsertime_command(command):
    print("Running command:", command)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    return process


def stream_output(process, stream_name, log_queue):
    while True:
        output = getattr(process, stream_name).readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(f"[{stream_name.upper()}] {output.strip()}")
            sys.stdout.flush()
            if stream_name == 'stdout' and "Starting: Intent" in output:
                log_queue.put(True)


def get_battery_status(serialID=None):
    battery_info = run_adb_command("dumpsys battery", serialID)
    battery_level = re.search(r"level: (\d+)", battery_info).group(1)
    current_charge = run_adb_command("cat /sys/class/power_supply/battery/charge_counter", serialID)
    return battery_level, current_charge


def capture_processes(serialID=None):
    process_output = run_adb_command("top -b -n 1 | grep -E '^[0-9]'", serialID)
    processes = {}
    for line in process_output.splitlines():
        parts = line.split()
        if len(parts) >= 12:
            processes[parts[0]] = (parts[11], parts[8], parts[10])
    return processes


def compare_and_log_changes(old_snapshot, new_snapshot):
    changes = []
    for pid, data in new_snapshot.items():
        if pid in old_snapshot and (old_snapshot[pid][1] != data[1] or old_snapshot[pid][2] != data[2]):
            changes.append(f"Name: {data[0]} | CPU%: {data[1]} | Time: {data[2]}")
    return changes


def get_component_names(components, serialID=None):
    thermalservice_output = run_adb_command("dumpsys thermalservice", serialID)
    pattern = re.compile(r"\{\.type = (\w+), \.name = (\w+),")
    types = {}
    components_lower = [comp.lower() for comp in components]
    for match in re.finditer(pattern, thermalservice_output):
        comp_type, name = match.groups()
        if comp_type.lower() in components_lower:
            if comp_type not in types:
                types[comp_type] = []
            types[comp_type].append(name)
    return types


def fetch_temperatures(component_names, serialID=None):
    temperatures = {}
    thermalservice_output = run_adb_command("dumpsys thermalservice", serialID)
    hal_section = thermalservice_output.split("Current temperatures from HAL:")[1]
    for comp_type, names in component_names.items():
        for name in names:
            pattern_str = r"Temperature\{mValue=([\d\.]+),.*?mName=" + re.escape(name) + r","
            temp_pattern = re.compile(pattern_str, re.IGNORECASE)
            temp_match = re.search(temp_pattern, hal_section)
            if temp_match:
                temperatures[name] = float(temp_match.group(1))
    return temperatures


def signal_handler(sig, frame):
    print('SIGINT received. Exiting...')
    # Perform any necessary cleanup actions here (e.g., close files, save data)
    sys.exit(0)


def main(directory, filename, package, activity, duration, components, serialID, start_method):
    last_snapshot = capture_processes(serialID)
    output_path = os.path.join(directory, filename)
    os.makedirs(directory, exist_ok=True)
    logging_started = False
    browsertime_process = None

    log_queue = queue.Queue()

    if start_method == "browsertime":
        browsertime_cmd = (
            "browsertime "
            "-b firefox --android "
            f"--firefox.geckodriverPath {os.path.expanduser('~/Repositories/mozilla-unified/target/debug/geckodriver')}"
            "--firefox.android.package org.mozilla.firefox "
            "--firefox.android.activity org.mozilla.fenix.IntentReceiverActivity "
            "--firefox.geckodriverArgs=\"--android-storage\" "
            "--firefox.geckodriverArgs=\"sdcard\" "
            "test.mjs "
            "-n 1 --maxLoadTime 60000 -vvv "
            "--pageCompleteCheck 'return true;'")
        browsertime_process = start_browsertime_command(browsertime_cmd)

        threading.Thread(target=stream_output, args=(browsertime_process, 'stdout', log_queue)).start()
        threading.Thread(target=stream_output, args=(browsertime_process, 'stderr', log_queue)).start()

    elif start_method == "manual":
        start_app(package, activity, serialID)
        logging_started = True
    elif start_method == "adb":
        logging_started = True
        print("adb start do nothing")
    components_names = get_component_names(components, serialID)
    total_duration = round(int(duration) / 15) * 15
    num_iterations = total_duration // 15
    with open(output_path, 'w+') as file:
        try:
            file.write(f"Components {components} matched to these names {components_names}\n\n")

            iteration = 0
            while iteration < num_iterations:
                try:
                    if log_queue.get_nowait():
                        logging_started = True
                except queue.Empty:
                    pass
                if logging_started:
                    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    battery_level, charge_counter = get_battery_status(serialID)
                    current_processes = capture_processes(serialID)
                    temperatures = fetch_temperatures(components_names, serialID)
                    file.write(f"[{(iteration + 1) * 15} seconds]\n")

                    file.write("-Battery info:\n")
                    file.write(f"   Battery level: {battery_level}\n")
                    file.write(f"   Charge Counter: {charge_counter}\n")
                    print(f"   Battery level: {battery_level}\n")
                    print(f"   Charge Counter: {charge_counter}\n")
                    file.write("-Temperature of components:\n")
                    for comp, temp in temperatures.items():
                        file.write(f"  {comp} Temperature: {temp}°C\n")
                    changes = compare_and_log_changes(last_snapshot, current_processes)
                    if changes:
                        file.write("\n-Running processes:\n")
                        for change in changes:
                            file.write(f"    {change}\n")
                    file.write("\n")
                    last_snapshot = current_processes
                    iteration += 1
                    print(f'finished iteration {iteration} and spent {iteration * 15} seconds')
                    time.sleep(15)

                # Check if browsertime process has ended and stop logging if so
                if browsertime_process and browsertime_process.poll() is not None:
                    logging_started = False
                    break
        except KeyboardInterrupt:
            print("Monitoring stopped.")

        if browsertime_process is not None:
            browsertime_process.kill()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('output_directory', type=str, help='Output directory path')
    parser.add_argument('output_filename', type=str, help='Output filename')

    if "--start_method" in sys.argv and sys.argv[sys.argv.index("--start_method") + 1] == "manual":
        parser.add_argument('package_name', type=str, help='Android package name (required for manual start)')
        parser.add_argument('activity_name', type=str, help='Activity name (required for manual start)')
        parser.add_argument('components', nargs='*', help='Optional list of components', default=[])
    else:
        parser.add_argument('--package_name', type=str, help='Android package name (optional for browsertime)')
        parser.add_argument('--activity_name', type=str, help='Activity name (optional for browsertime)')
        parser.add_argument('--components', nargs='*', help='Optional list of components', default=[])

    parser.add_argument('duration_seconds', type=int, help='Duration in seconds')
    parser.add_argument('--serialID', type=str, help='Optional serial ID', default=None)
    parser.add_argument(
        '--start_method',
        type=str,
        choices=[
            'browsertime',
            'manual',
            'adb'],
        default='browsertime',
        help='Method to start the app')

    args = parser.parse_args()

    main(args.output_directory, args.output_filename, args.package_name, args.activity_name,
         args.duration_seconds, args.components, args.serialID, args.start_method)
