# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import subprocess
import time
import re


def main(args):
    kill_existing_processes("org.mozilla")
    kill_existing_processes("com.android.chrome")
    kill_existing_processes("org.chromium.chrome")
    print("Waiting for three seconds.")
    time.sleep(3)

    print("Launching app.")

    if args.package.startswith("org.mozilla"):
        activity = args.package + "/org.mozilla.fenix.IntentReceiverActivity"
    else:
        # Assume Chrome
        activity = args.package + "/com.google.android.apps.chrome.IntentDispatcher"

    start_with_view_intent(activity, args.url)

    print("Waiting for %.1f seconds." % args.time)
    time.sleep(args.time)

    print("Gathering stats.")
    report_cpu_time(args.package)


def start_with_view_intent(activity, url):
    activity_start = subprocess.Popen(
        ['adb', 'shell', 'am', 'start-activity', '-d', url, '-a', 'android.intent.action.VIEW',
         activity]
    )
    activity_start.wait()


def report_cpu_time(package):
    adb_ps_command = subprocess.Popen(['adb', 'shell', 'ps', '-A', '-f'], stdout=subprocess.PIPE)
    try:
        psaf_output = subprocess.check_output(('grep', package), stdin=adb_ps_command.stdout)
        adb_ps_command.wait()
        psaf_lines = psaf_output.decode('utf-8').split('\n')

        # Sum up the CPU time of all matching processes.
        total_seconds = 0
        for line in psaf_lines:
            if line == '':
                continue
            # ['u0_a324', '14466', '1073', '70', '15:28:47', '?', '00:00:03', 'org.mozilla.fenix:tab30']
            columns = re.split(r'\s+', line)
            time_col = columns[6]
            [h, m, s] = time_col.split(":")
            total_seconds += ((int(h) * 60) + int(m)) * 60 + int(s)
        print("Total CPU time: %d seconds" % total_seconds)
    except subprocess.CalledProcessError as e:
        print("no processes matching %s found" % package)
        return


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
    parser = argparse.ArgumentParser(
        description='launch app with adb and check cumulative cpu time across matching processes',
        usage=('startup_cpu.py -p org.mozilla.fenix --url https://cnn.com/ --time 10')
    )
    parser.add_argument('-p', '--package', required=True, type=str, help="package")
    parser.add_argument('-u', '--url', required=True, type=str, help="URL")
    parser.add_argument('-t', '--time', type=float, help="time in seconds after which to report stats")
    args = parser.parse_args()
    main(args)
