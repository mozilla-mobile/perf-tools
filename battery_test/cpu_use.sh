#!/bin/bash
PACKAGE="org.mozilla.firefox"
ACTIVITY="org.mozilla.fenix.HomeActivity"


MONITORING_DURATION=3600


COLLECTION_INTERVAL=15


LOG_FILE="firefox_background_usage.txt"


adb shell am start -n "$PACKAGE/$ACTIVITY"

sleep 5


adb shell input keyevent KEYCODE_HOME


start_time=$(date +%s)

while [ $(( $(date +%s) - start_time )) -lt $MONITORING_DURATION ]; do

  adb shell dumpsys power | grep "Wake Locks" >> "$LOG_FILE"


  echo "\n--- CPU Usage at $(date) ---" >> "$LOG_FILE"
  adb shell top -n 1 | grep "$PACKAGE" >> "$LOG_FILE"


  current_app=$(adb shell dumpsys activity activities | grep mResumedActivity)
  if [[ $current_app == *"$ACTIVITY"* ]]; then

    adb shell input keyevent KEYCODE_HOME
  fi

  sleep $COLLECTION_INTERVAL
done


adb shell am force-stop "$PACKAGE"
