#!/bin/bash
PACKAGE="com.android.chrome"
ACTIVITY="com.google.android.apps.chrome.Main"
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

# script start
adb shell am start -n "$PACKAGE/$ACTIVITY"
sleep 4

adb shell uiautomator dump
adb pull /sdcard/window_dump.xml
sleep 1

## Using awk to extract the bounds attribute for the specified resource ID
TOOLBAR_BOUNDS=$(xmllint --xpath "string(//node[@resource-id='com.android.chrome:id/search_box_text']/@bounds)" "$XML_FILE")
TABS_TRAY_BUTTON_BOUNDS=$(xmllint --xpath "string(//node[@resource-id='com.android.chrome:id/tab_switcher_button']/@bounds)" "$XML_FILE")
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

ADD_TAB_BUTTON_BOUNDS=$(xmllint --xpath "string(//node[@resource-id='com.android.chrome:id/new_tab_view_button']/@bounds)" "$XML_FILE")
sleep 1

ADD_TAB_BUTTON_X_COORDINATE=$((($(echo "$ADD_TAB_BUTTON_BOUNDS" | awk -F'[][]' '{print $2}' | awk -F',' '{print $1}') + $(echo "$ADD_TAB_BUTTON_BOUNDS" | awk -F'[][]' '{print $4}' | awk -F',' '{print $1}')) / 2))
ADD_TAB_BUTTON_Y_COORDINATE=$((($(echo "$ADD_TAB_BUTTON_BOUNDS" | awk -F'[][]' '{print $2}' | awk -F',' '{print $2}') + $(echo "$ADD_TAB_BUTTON_BOUNDS" | awk -F'[][]' '{print $4}' | awk -F',' '{print $2}')) / 2))

rm window_dump.xml
adb shell input keyevent KEYCODE_BACK
sleep 1

function tapToFocusToolbar() {
  # tap on the url toolbar
  adb shell input tap $TOOLBAR_X_COORDINATE $TOOLBAR_Y_COORDINATE
  sleep 2
}

function inputTextToToolbar() {
  # input url
  adb shell input text $1
  sleep 2
}

function tapEnterAndWait5s() {
  # press enter
  adb shell input keyevent 66
  sleep 5
}

function tapEnterAndWait10s() {
  # press enter
  adb shell input keyevent 66
  sleep 10
}

function performScrollDown() {
  # scroll down
  adb shell input swipe 500 500 500 300
  adb shell input swipe 500 500 500 300
  adb shell input swipe 500 500 500 300
  sleep 2
}

function performScrollUp() {
  # scroll up
  adb shell input swipe 500 300 500 500
  adb shell input swipe 500 300 500 500
  adb shell input swipe 500 300 500 500
  sleep 2
}

function tapToOpenTabsTray() {
  # tap to open tabs tray
  adb shell input tap $TABS_TRAY_BUTTON_X_COORDINATE $TABS_TRAY_BUTTON_Y_COORDINATE
  sleep 2
}

function tapToAddTab() {
  # tap to open another tab
  adb shell input tap $ADD_TAB_BUTTON_X_COORDINATE $ADD_TAB_BUTTON_Y_COORDINATE
  sleep 3
}

function addTab() {
  tapToOpenTabsTray
  tapToAddTab
}

function simple_browsing_single_site() {
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

# test starts after this line
simple_browsing_single_site $URL_BOOKING
addTab
simple_browsing_single_site $URL_MOZILLA
addTab
simple_browsing_single_site $URL_IMDB
addTab
simple_browsing_single_site $URL_WIKIPEDIA

# uncomment this line if you want to stop the app
# adb shell am force-stop $PACKAGE
