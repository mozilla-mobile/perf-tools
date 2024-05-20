import re
import csv
from collections import defaultdict


input_file_path = './chrome_test/chrome_battery_video_playback.txt'
output_file_path = './chrome_test/chrome_battery_video_playback_test.csv'
process_file_path = './chrome_test/chrome_battery_video_playback_test_process.csv'

timestamp_regex = re.compile(r"\[(\d+) seconds\]")
battery_level_regex = re.compile(r"\s*Battery level:\s+(\d+)")
charge_counter_regex = re.compile(r"\s*Charge Counter:\s+(\d+)")
first_temperature_line_regex = re.compile(r"-\s*Temperature of components:\s*(\w+ Temperature:\s+[\d.]+°C)")
temperature_regex = re.compile(r"\s*(\w+) Temperature:\s+([\d.]+)°C")
process_regex = re.compile(r"\s*Name:\s+(.*?)\s+\|\s+CPU%:\s+([\d.]+)\s+\|\s+Time:\s+([\d:\.]+)")
keywords = ['firefox', 'google', 'chrome']

data = []
process_data = defaultdict(list)

with open(input_file_path, 'r') as file:
    current_entry = {}
    for line in file:

        timestamp_match = timestamp_regex.match(line)
        if timestamp_match:

            if current_entry:
                data.append(current_entry)
            current_entry = {'Interval Time': int(timestamp_match.group(1))}
            current_timestamp = int(timestamp_match.group(1))

        battery_level_match = battery_level_regex.search(line)
        if battery_level_match:
            current_entry['Battery Level'] = int(battery_level_match.group(1))

        charge_counter_match = charge_counter_regex.search(line)
        if charge_counter_match:
            current_entry['Charge Counter'] = int(charge_counter_match.group(1))

        if line.startswith("-Temperature of components:"):
            temperatures = []

            component_match = first_temperature_line_regex.match(line)

            if component_match:
                first_component = component_match.group(1)
                temperatures.append(first_component.strip())

            for temp_line in file:
                temperature_match = temperature_regex.match(temp_line)
                if temperature_match:
                    temperatures.append(temp_line.strip())
                else:
                    break

            current_entry['Temperature of Components'] = "\n".join(temperatures)

        process_match = process_regex.match(line)
        if process_match:

            process_name = process_match.group(1).strip()
            process_cpu = process_match.group(2).strip()
            process_time = process_match.group(3).strip()

            process_data[current_timestamp].append({
                "Process Name": process_name,
                "CPU%": process_cpu,
                "Time": process_time
            })  # A

    if current_entry:
        data.append(current_entry)


for timestamp in process_data:
    num_processes = len(process_data[timestamp])

    for entry in data:
        if entry['Interval Time'] == timestamp:
            entry['Number of Processes'] = num_processes
            break
    else:
        data.append({'Interval Time': timestamp, 'Number of Processes': num_processes})

total_charge_loss = data[0]['Charge Counter'] - data[-1]['Charge Counter']


total_row = {'Interval Time': 'Total',
             'Battery Level': None,
             'Charge Counter': total_charge_loss,
             'Temperature of Components': None,
             'Number of Processes': None}


data.append(total_row)

with open(output_file_path, 'w', newline='') as csvfile:

    fieldnames = [
        'Interval Time',
        'Battery Level',
        'Charge Counter',
        'Temperature of Components',
        'Number of Processes']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for entry in data:
        writer.writerow(entry)

    data.append(total_row)

aggregated_process_data = defaultdict(list)
for timestamp, processes in process_data.items():
    interval_start = (timestamp // 15) * 15
    aggregated_process_data[interval_start].extend(processes)

with open(process_file_path, 'w', newline='') as csvfile:
    fieldnames = ['Interval Time', 'Process Name', 'CPU%', 'Time']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()


for timestamp in process_data:
    num_processes = len(process_data[timestamp])

    for entry in data:
        if entry['Interval Time'] == timestamp:
            entry['Number of Processes'] = num_processes
            break
    else:
        data.append({'Interval Time': timestamp, 'Number of Processes': num_processes})

    with open(process_file_path, 'w', newline='') as csvfile:
        fieldnames = ['Interval Time', 'Process Name', 'CPU%', 'Time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        current_interval = None

        for timestamp, processes in aggregated_process_data.items():
            for process in processes:
                if any(keyword in process['Process Name'] for keyword in keywords):
                    if current_interval != timestamp:
                        current_interval = timestamp
                        writer.writerow({'Interval Time': timestamp,
                                         'Process Name': process['Process Name'],
                                         'CPU%': process['CPU%'],
                                         'Time': process['Time']})
                    else:
                        writer.writerow({'Interval Time': '',
                                         'Process Name': process['Process Name'],
                                         'CPU%': process['CPU%'],
                                         'Time': process['Time']})
