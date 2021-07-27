# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import urllib.request
import subprocess
import analyze_durations
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

DESCRIPTION = """ Allows to get startup performance metrics between two dates.
This can backfill numbers for either daily nightlys or for two commits.
"""

NIGHTLY_BASE_URL = ("https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/mobile.v2.fenix.nightly.{date}."
                    + "latest.armeabi-v7a/artifacts/public%2Fbuild%2Farmeabi-v7a%2Ftarget.apk")
BACKFILL_DIR = "backfill_output"
DURATIONS_OUTPUT_FILE_TEMPLATE = "durations_for_{apk}.txt"
ANALYZED_DURATIONS_FILE_TEMPLATE = "{apk_name}_perf_results.txt"

KEY_NAME = "name"
KEY_DATETIME = "date"

DATETIME_FORMAT = "%Y.%m.%d"


def parse_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument("path_to_startup_script",
                        help="Path to the measure_start_up.py script needed to gather startupperformance metrics")
    parser.add_argument("package_id", help="Package id associated with the apk to install / uninstall")
    parser.add_argument("start", type=lambda date: datetime.strptime(date, DATETIME_FORMAT),
                        help="Date to start the backfill")
    parser.add_argument("-e", "--enddate", type=lambda date: datetime.strptime(date, DATETIME_FORMAT),
                        default=datetime.now(),
                        help="end date to backfill until.If empty, default will be the current date")
    parser.add_argument("-t", "--type", required=True, choices=["nightly", "commits"],
                        help="The type of system the backfill should run performance analysis on")

    parser.add_argument("-r", "--repository_path",
                        help="Path to the repository where the commits will be gotten from")
    parser.add_argument("-c", "--cleanup", action="store_true",
                        help="Remove all apks downloaded since they can takeup lots of space")

    return parser.parse_args()


def fetch_nightly(download_date):
    download_date_string = datetime.strftime(download_date, DATETIME_FORMAT)
    nightly_url = NIGHTLY_BASE_URL.format(date=download_date_string)
    filename = "nightly_" + download_date_string.replace(".", "_") + ".apk"
    try:
        urllib.request.urlretrieve(nightly_url, filename=filename)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            print("\n\nThe apk for {date} is not available at this {url}".format(date=download_date, url=nightly_url),
                  file=sys.stderr)
        return None

    # TODO: Could add build type, architecture, etc...
    return {KEY_NAME: filename, KEY_DATETIME: download_date}


def get_date_array_for_range(startdate, enddate):
    delta_dates = (enddate - startdate).days + 1
    return [startdate + timedelta(days=i) for i in range(delta_dates)]


def download_nightly_for_range(array_of_dates):
    # TODO if file exist and no -f option
    apk_metadata_array = [fetch_nightly(date) for date in array_of_dates]
    return [e for e in apk_metadata_array if e is not None]


def install_apk(apk_build_path):
    install_proc = subprocess.run(["adb", "install", apk_build_path], check=False, capture_output=True)
    if install_proc.returncode != 0:
        print(("\n\nSomething went wrong while installing the following apk: {apk} . The associated error message was:"
               "\n\n {error}".format(apk=apk_build_path, error=install_proc.stderr.strip(b'\n'))),
              file=sys.stderr)
        return False
    return True


def uninstall_apk(package_id):
    uninstall_proc = subprocess.run(["adb", "uninstall", package_id], check=False, capture_output=True)
    if uninstall_proc.returncode != 0:
        print(("\n\nSomething with the uninstalling {package_id} went wrong. The associated error message was:\n\n"
               " {error}".format(package_id=package_id, error=uninstall_proc.stderr.strip(b"\n"))),
              file=sys.stderr)


def run_measure_start_up_script(path_to_measure_start_up_script, durations_output_path):
    subprocess.run([path_to_measure_start_up_script, "nightly", "cold_view_nav_start", durations_output_path],
                   stdout=subprocess.PIPE, check=False)


def analyze_nightly_for_one_build(package_id, path_to_measure_start_up_script, apk_metadata):
    uninstall_apk(package_id)

    was_install_successful = install_apk(apk_metadata[KEY_NAME])
    if was_install_successful:
        Path(BACKFILL_DIR).mkdir(parents=True, exist_ok=True)

        apk_name = apk_metadata[KEY_NAME].split(".")[0]

        # TODO fix verify if file exist to have -f in this script
        durations_output_path = os.path.join(BACKFILL_DIR, DURATIONS_OUTPUT_FILE_TEMPLATE.format(apk=apk_name))
        analyzed_durations_path = os.path.join(BACKFILL_DIR, ANALYZED_DURATIONS_FILE_TEMPLATE.format(apk_name=apk_name))

        run_measure_start_up_script(path_to_measure_start_up_script, durations_output_path)
        get_result_from_durations(durations_output_path, analyzed_durations_path)


def get_result_from_durations(start_up_durations_path, analyzed_path):
    try:
        filetype = analyze_durations.detect_filetype(start_up_durations_path)
    except FileNotFoundError:
        print(("The file {file} doesn't exist, this is probably due to a failure in running"
               "the measure_start_up.py for the apk with the according date").format(file=start_up_durations_path),
              file=sys.stderr)
        return

    measurement_arr = filetype.read_from(start_up_durations_path)
    stats = analyze_durations.to_stats(measurement_arr)
    analyze_durations.save_output(stats, analyzed_path)


def run_performance_analysis_on_nightly(package_id, path_to_measure_start_up_script, array_of_apk_path):
    for apk_path in array_of_apk_path:
        analyze_nightly_for_one_build(package_id, path_to_measure_start_up_script, apk_path)


def cleanup(array_of_apk_path):
    for i in array_of_apk_path:
        subprocess.run(["rm", i[KEY_NAME]])


def main():
    args = parse_args()
    if args.type == "commits" and args.fenix_path is None:
        raise Exception("Provide the path to your fenix repository to run this script with the commits option")

    array_of_dates = get_date_array_for_range(args.start, args.enddate)

    if args.type == "nightly":
        array_of_apk_metadata = download_nightly_for_range(array_of_dates)

    run_performance_analysis_on_nightly(args.package_id, args.path_to_startup_script, array_of_apk_metadata)

    if args.cleanup is True:
        cleanup(array_of_apk_metadata)


if __name__ == '__main__':
    main()
