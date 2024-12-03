import re
import datetime

def parse_and_format_file(input_file, output_file):
    with open(input_file, 'r') as file:
        lines = file.readlines()

    battery_info_pattern = re.compile(r'Battery level: (\d+)|Charge Counter: (\d+)')
    running_tasks_pattern = re.compile(r'Name: ([^|]+) \| CPU%: (\d+\.\d+) \| Time: (\d+:\d+\.\d+)')
    timestamp_pattern = re.compile(r'Timestamp: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+N)')

    output_lines = [
        "Components ['GPU', 'CPU'] matched to these names {'GPU': ['G3D'], 'CPU': ['BIG', 'MID', 'LITTLE']}\n"
    ]

    time_intervals = 15  # Start with 15 seconds
    current_battery_level = None
    current_charge_counter = None
    running_tasks = []

    for line in lines:
        battery_match = battery_info_pattern.search(line)
        task_match = running_tasks_pattern.search(line)
        timestamp_match = timestamp_pattern.search(line)

        if battery_match:
            if battery_match.group(1):
                current_battery_level = battery_match.group(1)
            if battery_match.group(2):
                current_charge_counter = battery_match.group(2)

        elif task_match:
            running_tasks.append(f"    Name: {task_match.group(1).strip()} | CPU%: {task_match.group(2)} | Time: {task_match.group(3)}\n")

        elif timestamp_match:
            if current_battery_level and current_charge_counter:
                output_lines.append(f"\n[{time_intervals} seconds]\n")
                output_lines.append(f"-Battery info:\n   Battery level: {current_battery_level}\n   Charge Counter: {current_charge_counter}\n")
                output_lines.append("-Running processes:\n")
                output_lines.extend(running_tasks)
                running_tasks.clear()
                time_intervals += 15

    with open(output_file, 'w') as file:
        file.writelines(output_lines)

# Use the function
input_file = '../chrome_test/s21_output_chrome_video.txt'
output_file = '../chrome_test/s21_output_chrome_video_playback.txt'
parse_and_format_file(input_file, output_file)
