# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import argparse
import subprocess
import time
import os
import signal


#This script records the phone either through intent or simulating user touch for the purpose of generating videos that are consistent.
#The consistency allows us to compare said video.
def main(args):
    method = args.input
    recording_name = './sdcard/output.mp4'

    if args.output is not None:
            recording_name = './sdcard/' + args.output
    if method in 'touch' and (args.coordinate_x is None or args.coordinate_y is None):
        print('--touch requires --coordinate-x <coordinate> --coordinate-y <coordinate> to use the touch input')
        sys.exit()
    # if method in 'intent' and args.package is None:
    #     print('--intent requires --package <your.package.name>')
    #     sys.exit()

    check_for_existing_process()
    record_process = subprocess.Popen(['adb', 'shell','screenrecord'] + [recording_name])
    time.sleep(3)

    #TODO allow intent trigger
    #if method in 'intent':
        # record_with_intent(args.package)
    #else:
    simulate_input(args.coordinate_x, args.coordinate_y)
    pull_recording(record_process, recording_name)

# def record_with_intent(package):
#     activity_start = subprocess.Popen(['adb', 'shell', 'am', 'start-activity', package +'/.App', '--ez finishonboarding true'])
#     activity_start.wait()

def simulate_input(x,y):
    tap_event = subprocess.Popen(['adb', 'shell', 'input', 'tap'] + [str(x),str(y)])
    tap_event.wait()

def pull_recording(record_process, recording_name):
    time.sleep(5)
    record_process.kill()
    time.sleep(5)
    proc = subprocess.Popen(['adb', 'pull'] + [recording_name])
    proc.wait()

def check_for_existing_process():
    adb_ps_command = subprocess.Popen(['adb', 'shell', 'ps', '-A', '-o', 'NAME'], stdout=subprocess.PIPE)
    try:
        mozilla_processes = subprocess.check_output(('grep', 'org.mozilla'),  stdin=adb_ps_command.stdout)
        adb_ps_command.wait()
        packages_found = mozilla_processes.decode('utf-8').split('\n')
        for package in packages_found:
            if package is '':
                continue
            kill_process=subprocess.Popen(['adb','shell', 'am','force-stop']+[package])
            kill_process.wait()
            print('Successfully killed process %s' % package)
    except subprocess.CalledProcessError as e:
        print("no mozilla processes found")
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='record video through adb', usage='record_adb.py --input <touch> --coordinate-x and --cordinate-y  --output <name.mp4>')
    #add intent later
    parser.add_argument('-i','--input', required=True, choices=("touch"))
    parser.add_argument('-cx','--coordinate-x', type=int, help="X position of touch event")
    parser.add_argument('-cy','--coordinate-y', type=int, help="Y position of touch event")
    #parser.add_argument('-p','--package', type=str, help='package name to record if intent is used')
    parser.add_argument('-o','--output', type=str, help="output name of file")
    args = parser.parse_args()
    main(args)
