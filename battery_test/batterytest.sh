#!/bin/bash

APP_PACKAGE='com.android.chrome'
MAIN_ACTIVITY='com.google.android.apps.chrome.Main'

adb shell am start -n "$APP_PACKAGE/$MAIN_ACTIVITY" -a com.example.action.START_RECORDING

sleep 5


LAST_PROCESS_SNAPSHOT="last_processes.txt"
CURRENT_PROCESS_SNAPSHOT="current_processes.txt"


start_time=$(date +%s)
end_time=$((start_time + 1800))


function get_battery_status() {
    timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    echo "Timestamp: $timestamp"
    echo "Battery level:" $(adb shell dumpsys battery | grep level | awk '{print $2}')

    current_charge=$(adb shell cat /sys/class/power_supply/battery/charge_counter)
    echo "Timestamp: Charge Counter: $current_charge"
}


function capture_processes() {
    adb shell top -b -n 1 | grep -E '^[0-9]' | awk '{print $1, $12, $9, $11}' > "$CURRENT_PROCESS_SNAPSHOT"
}


function compare_and_log_changes() {
    if [ -f "$LAST_PROCESS_SNAPSHOT" ]; thenz
        echo "Running tasks with changed times:"
        awk 'NR==FNR {a[$1] = $4; next} ($1 in a) && (a[$1] != $4)' "$LAST_PROCESS_SNAPSHOT" "$CURRENT_PROCESS_SNAPSHOT" | \
        awk '{print " Name:", $2, "| CPU%:", $3, "| Time:", $4}'
    fi
    cp "$CURRENT_PROCESS_SNAPSHOT" "$LAST_PROCESS_SNAPSHOT"
}


capture_processes


while [ $(date +%s) -lt $end_time ]; do
    get_battery_status
    capture_processes
    compare_and_log_changes
    sleep 15
done
