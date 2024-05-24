# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import argparse
import subprocess
import time


# This script records a video of the phone screen and triggers app activity in one of three ways:
#  - mode == "touch": Simulates user touch at the specified coordinates
#  - mode == "launch": Launches an app with the .MainActivity
#  - mode == "applink": Launches an app with the VIEW intent and a URL
# We can then compare the recorded videos across browsers.
def main(args):
    mode = args.mode
    device_path = './sdcard/output.mp4'

    if mode == 'touch' and (args.coordinate_x is None or args.coordinate_y is None):
        print('--mode touch requires --coordinate-x <coordinate> --coordinate-y <coordinate> '
              'to use the touch input. Enable the touch coordinate overlay in the Android debug '
              'settings to find the right coordinates.')
        sys.exit()

    if mode == 'launch' and (args.package is None):
        print('--mode launch requires --package argument')
        sys.exit()

    if mode == 'applink' and (args.url is None or args.package is None):
        print('--mode applink requires --url and --package arguments')
        sys.exit()

    kill_existing_processes("org.mozilla")
    kill_existing_processes("com.android.chrome")
    kill_existing_processes("org.chromium.chrome")
    time.sleep(3)

    # Start the recording. screenrecord --bugreport puts timestamps at the top of the video and adds
    # a frame with device information at the beginning.
    record_process = subprocess.Popen(['adb', 'shell', 'screenrecord', '--bugreport'] + [device_path])
    time.sleep(3)

    if mode == "touch":
        simulate_input(args.coordinate_x, args.coordinate_y)
    elif mode == "launch":
        # The launch activity name depends on the app.
        # To find the right activity name, run `adb shell pm dump <packagename>` and look for an
        # activity with `Action: "android.intent.action.MAIN"` and
        # `Category: "android.intent.category.LAUNCHER"`.
        if args.package.startswith("org.mozilla"):
            activity = args.package + "/.App"
        else:
            # Assume Chrome
            activity = args.package + "/com.google.android.apps.chrome.Main"
        record_with_activity(activity)
    else:
        # The app link activity name depends on the app.
        # To find the right activity name, run `adb shell pm dump <packagename>` and look for an
        # activity with `Action: "android.intent.action.VIEW"` and `Category: "android.intent.category.BROWSABLE"`.
        if args.package.startswith("org.mozilla"):
            activity = args.package + "/org.mozilla.fenix.IntentReceiverActivity"
        else:
            # Assume Chrome
            activity = args.package + "/com.google.android.apps.chrome.IntentDispatcher"
        record_with_view_intent(activity, args.url)

    time.sleep(5)
    record_process.kill()
    time.sleep(5)
    pull_recording(device_path, args.output)


def simulate_input(x, y):
    tap_event = subprocess.Popen(['adb', 'shell', 'input', 'tap'] + [str(x), str(y)])
    tap_event.wait()


def record_with_activity(activity):
    activity_start = subprocess.Popen(
        ['adb', 'shell', 'am', 'start-activity',
         '-a', 'android.intent.action.VIEW', activity]
    )
    activity_start.wait()


def record_with_view_intent(activity, url):
    activity_start = subprocess.Popen(
        ['adb', 'shell', 'am', 'start-activity', '-d', url,
         '-a', 'android.intent.action.VIEW', activity]
    )
    activity_start.wait()


def pull_recording(device_path, output):
    proc = subprocess.Popen(['adb', 'pull', device_path, output])
    proc.wait()


def kill_existing_processes(package_substr):
    adb_ps_command = subprocess.Popen(['adb', 'shell', 'ps', '-A', '-o', 'NAME'], stdout=subprocess.PIPE)
    try:
        matching_processes = subprocess.check_output(('grep', package_substr), stdin=adb_ps_command.stdout)
        adb_ps_command.wait()
        packages_found = matching_processes.decode('utf-8').split('\n')
        for package in packages_found:
            if package == '':
                continue
            kill_process = subprocess.Popen(['adb', 'shell', 'am', 'force-stop'] + [package])
            kill_process.wait()
            print('Successfully killed process %s' % package)
    except subprocess.CalledProcessError as e:
        print("no processes matching %s found, not killing any" % package_substr)
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='record video through adb',
                                     usage=('record_adb.py --mode touch -cx 660 -cy 2222 '
                                            '--output <name.mp4>'))

    parser.add_argument('-m', '--mode', required=True, choices=("touch", "launch", "applink"))
    parser.add_argument('-cx', '--coordinate-x', type=int, help="X position of touch event")
    parser.add_argument('-cy', '--coordinate-y', type=int, help="Y position of touch event")
    parser.add_argument('-p', '--package', type=str, help="App package for launch / applink")
    parser.add_argument('-u', '--url', type=str, help="applink URL")
    parser.add_argument('-o', '--output', required=True, type=str, help="output file path")
    args = parser.parse_args()
    main(args)
