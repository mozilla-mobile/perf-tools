#!/bin/bash
PACKAGE="org.mozilla.firefox"
ACTIVITY="org.mozilla.fenix.HomeActivity"
XML_FILE="window_dump.xml"

# Test urls
URL_REDDIT="https://www.reddit.com/r/all"
URL_INSTAGRAM="https://www.instagram.com/"
URL_INSTAGRAM_EXPLORE="https://www.instagram.com/explore"
URL_FACEBOOK="https://www.facebook.com"
URL_TMZ="https://tmz.com"
URL_PEREZ="https://perezhilton.com"
URL_WIKI="https://wikipedia.org/wiki/Student%27s_t-test",
URL_SEARCH_FOX="https://searchfox.org/mozilla-central/source/toolkit/components/telemetry/Histograms.json",
URL_BUZZFEED="https://buzzfeed.com"
URL_CNN="https://cnn.com"


# Set the total duration in seconds (30 minutes = 1800 seconds)
TOTAL_DURATION=900
declare -i TOTAL_DURATION

# Set the duration for each website in seconds (5 minutes = 300 seconds)
WEBSITE_DURATION=10
declare -i WEBSITE_DURATION

websites=("$URL_INSTAGRAM" ,"$URL_REDDIT", "$URL_INSTAGRAM_EXPLORE", "$URL_FACEBOK","$URL_TMZ", "$URL_PEREZ","$URL_WIKI", "$URL_SEARCH_FOX", "$URL_BUZZFEED","$URL_CNN" )

python3 battery_test.py firefox_text firefox_regular_browsing_adb 1800 \
   --start_method adb --serialID 192.168.2.132:5555 --components GPU CPU &
battery_test_pid=$!             # Get the process ID (PID)
battery_test_pgid=$(ps -o pgid= -p $battery_test_pid)  # Get the process group ID (PGID)

trap 'echo "Cleaning up and exiting..."; kill -- -$battery_test_pgid; exit' SIGINT

# script start
adb -s 192.168.2.132:5555 shell am start -n "$PACKAGE/$ACTIVITY"
sleep 4

adb -s 192.168.2.132:5555 shell uiautomator dump
adb -s 192.168.2.132:5555 pull /sdcard/window_dump.xml
sleep 1

TOOLBAR_BOUNDS=$(xmllint --xpath "string(//node[@resource-id='org.mozilla.firefox:id/toolbar']/@bounds)" "$XML_FILE")
TABS_TRAY_BUTTON_BOUNDS=$(xmllint --xpath "string(//node[@resource-id='org.mozilla.firefox:id/counter_box']/@bounds)" "$XML_FILE")
sleep 1

# Extract and calculate center coordinates in a single line
TOOLBAR_X_COORDINATE=$((($(echo "$TOOLBAR_BOUNDS" | awk -F'[][]' '{print $2}' | awk -F',' '{print $1}') + $(echo "$TOOLBAR_BOUNDS" | awk -F'[][]' '{print $4}' | awk -F',' '{print $1}')) / 2))
TOOLBAR_Y_COORDINATE=$((($(echo "$TOOLBAR_BOUNDS" | awk -F'[][]' '{print $2}' | awk -F',' '{print $2}') + $(echo "$TOOLBAR_BOUNDS" | awk -F'[][]' '{print $4}' | awk -F',' '{print $2}')) / 2))
TABS_TRAY_BUTTON_X_COORDINATE=$((($(echo "$TABS_TRAY_BUTTON_BOUNDS" | awk -F'[][]' '{print $2}' | awk -F',' '{print $1}') + $(echo "$TABS_TRAY_BUTTON_BOUNDS" | awk -F'[][]' '{print $4}' | awk -F',' '{print $1}')) / 2))
TABS_TRAY_BUTTON_Y_COORDINATE=$((($(echo "$TABS_TRAY_BUTTON_BOUNDS" | awk -F'[][]' '{print $2}' | awk -F',' '{print $2}') + $(echo "$TABS_TRAY_BUTTON_BOUNDS" | awk -F'[][]' '{print $4}' | awk -F',' '{print $2}')) / 2))

# tap to open tabs tray
adb shell input tap $TABS_TRAY_BUTTON_X_COORDINATE $TABS_TRAY_BUTTON_Y_COORDINATE
sleep 2

# take ss
adb shell uiautomator dump
adb pull /sdcard/window_dump.xml

ADD_TAB_BUTTON_BOUNDS=$(xmllint --xpath "string(//node[@content-desc='Add tab']/@bounds)" "$XML_FILE")
sleep 1

ADD_TAB_BUTTON_X_COORDINATE=$((($(echo "$ADD_TAB_BUTTON_BOUNDS" | awk -F'[][]' '{print $2}' | awk -F',' '{print $1}') + $(echo "$ADD_TAB_BUTTON_BOUNDS" | awk -F'[][]' '{print $4}' | awk -F',' '{print $1}')) / 2))
ADD_TAB_BUTTON_Y_COORDINATE=$((($(echo "$ADD_TAB_BUTTON_BOUNDS" | awk -F'[][]' '{print $2}' | awk -F',' '{print $2}') + $(echo "$ADD_TAB_BUTTON_BOUNDS" | awk -F'[][]' '{print $4}' | awk -F',' '{print $2}')) / 2))

rm window_dump.xml
adb shell input keyevent KEYCODE_BACK
sleep 1


function checkGoogleSignIn(){
   adb shell

}

function inputTextToToolbar() {
 # Move the focus to the URL toolbar
 adb -s 192.168.2.132:5555 shell input tap $TOOLBAR_X_COORDINATE $TOOLBAR_Y_COORDINATE
 sleep 1

 #key event to delete
 adb -s 192.168.2.132:5555 shell input keyevent 67
 echo "erased"
 sleep 1

 # input url
 adb -s 192.168.2.132:5555 shell input text $1
 sleep 1

 adb -s 192.168.2.132:5555 shell input keyevent 67
}

function tapEnterAndWait5s() {
 # press enter
 adb -s 192.168.2.132:5555 shell input keyevent 66
 sleep 5
}

function tapEnterAndWait10s() {
 # press enter
 adb -s 192.168.2.132:5555 shell input keyevent 66
 sleep 10
}

function performScrollDown() {
 # scroll down
 adb -s 192.168.2.132:5555 shell input swipe 500 500 500 300
 adb -s 192.168.2.132:5555 shell input swipe 500 500 500 300
 adb -s 192.168.2.132:5555 shell input swipe 500 500 500 300
 sleep 2
}

function performScrollUp() {
 # scroll up
 adb -s 192.168.2.132:5555 shell input swipe 500 300 500 500
 adb -s 192.168.2.132:5555 shell input swipe 500 300 500 500
 adb -s 192.168.2.132:5555 shell input swipe 500 300 500 500
 sleep 2
}

function tapToOpenTabsTray() {
 # tap to open tabs tray
 adb -s 192.168.2.132:5555 shell input tap $TABS_TRAY_BUTTON_X_COORDINATE $TABS_TRAY_BUTTON_Y_COORDINATE
 sleep 2
}

function tapToAddTab() {
 # tap to open another tab
 adb -s 192.168.2.132:5555 shell input tap $ADD_TAB_BUTTON_X_COORDINATE $ADD_TAB_BUTTON_Y_COORDINATE
 sleep 3
}

function addTab() {
 tapToOpenTabsTray
 tapToAddTab
}

function simple_browsing_single_site() {
 echo "starting test for"
 echo $1
 tapToFocusToolbar
 inputTextToToolbar $1
 tapEnterAndWait10s
 performScrollDown
 performScrollUp
}

function simple_browsing_two_sites() {
 tapToFocusToolbar
 inputTextToToolbar $1
 tapEnterAndWait10s
 performScrollDown
 performScrollUp
 tapToFocusToolbar
 inputTextToToolbar $2
 tapEnterAndWait10s
 performScrollDown
 performScrollUp
}
# at this point our system is ready, the buttons' coordinates are generated

# Start of the loop
# Start of the loop
start_time=$(date +%s)
declare -i start_time
declare -i TOTAL_DURATION

# Set the total duration in seconds (30 minutes = 1800 seconds)
TOTAL_DURATION=1800

start_time=$(date +%s)
declare -i start_time
declare -i TOTAL_DURATION

# Set the total duration in seconds (30 minutes = 1800 seconds)
TOTAL_DURATION=1800

current_time=$(date +%s)
while [ $((current_time - start_time)) -lt $TOTAL_DURATION ]; do

    for url in "${websites[@]}"; do
        tapToFocusToolbar
        echo "Navigating to $url"

        inputTextToToolbar "$url"
        tapEnterAndWait10s
        sleep 2

        # Start timer for the current website
        website_start_time=$(date +%s)

        while [ $(( $(date +%s) - website_start_time )) -lt $WEBSITE_DURATION ]; do
            performScrollDown
            sleep 2  # Adjust the sleep for scrolling speed
        done

        # Break out of the for loop if the total time is reached
        if [[ $(date +%s) -ge $((start_time + TOTAL_DURATION)) ]]; then
            echo "Total duration reached, breaking out of the loop"
            break;
        fi

        addTab  # Add a new tab for the next website
    done
  current_time=$(date +%s)
done






# Cleanup and closing
adb -s 192.168.2.132:5555 shell am force-stop $PACKAGE
# Remove the window dump file
rm window_dump.xml
