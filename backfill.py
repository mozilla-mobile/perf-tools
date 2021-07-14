import argparse
import urllib.request
import subprocess
import analyze_durations
import os
from datetime import datetime, timedelta

# first parse argument
# second validate argument
# first is get nightly build
#  get nightly from taskluster
# install the builds
# run the builds


NIGHTLY_BASE_URL = "https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/mobile.v2.fenix.nightly.{date}.latest.armeabi-v7a/artifacts/public%2Fbuild%2Farmeabi-v7a%2Ftarget.apk"
BACKFILL_DIR = "backfill_output"
DURATIONS_OUTPUT_FILE = "save.txt"

KEY_NAME = "name"
KEY_DATETIME = "date"
def fetch_nightly(download_date):
    download_date_string = datetime.strftime(download_date,"%Y.%m.%d")
    nightly_url = NIGHTLY_BASE_URL.format(date=download_date_string)
    filename = "nightly_" + download_date_string.replace(".","_") +".apk"

    #TODO: Could add build type, architecture, etc...
    apk_metadata = {KEY_NAME: filename, KEY_DATETIME: download_date}

    urllib.request.urlretrieve(nightly_url, filename=filename)
    return apk_metadata

def download_nightly_for_range(days):
    download_date = datetime(year=2021, month=6, day=1)
    apk_metadata_array = []
    for i in range(days):
        download_date = download_date + timedelta(days=i)
        apk_metadata_array.append(fetch_nightly(download_date))
    return apk_metadata_array

def install_apk(apk_build_path):
    subprocess.run(["adb","install",apk_build_path], check=True)

def uninstall_apk(package_id):
    subprocess.run(["adb", "uninstall",package_id])

#run ./fenix/tools/measure_start_up.py nightly cold_view_nav_start <path>
def run_measure_start_up_script(durations_output_path):
    #TODO: handle errors from measure start up script (i.e output_dir already exist)
    subprocess.run(["../mleclair/fenix/tools/measure_start_up.py","nightly","cold_view_nav_start",durations_output_path])

def get_result_from_durations(start_up_durations_path, analyzed_path):
    filetype = analyze_durations.detect_filetype(start_up_durations_path)
    measurement_arr = filetype.read_from(start_up_durations_path)
    stats = analyze_durations.to_stats(measurement_arr)
    analyze_durations.save_output(stats, analyzed_path)

def analyze_nightly_for_one_build(apk_metadata):
    uninstall_apk("org.mozilla.fenix")
    install_apk(apk_metadata[KEY_NAME])

    durations_output_path = os.path.join(BACKFILL_DIR, DURATIONS_OUTPUT_FILE)
    analyzed_durations_filename = "{apk_name}_{apk_datetime}.txt".format(apk_name=apk_metadata[KEY_NAME], apk_datetime = apk_metadata[KEY_DATETIME])
    analyzed_durations_path = os.path.join(BACKFILL_DIR, analyzed_durations_filename)

    run_measure_start_up_script(durations_output_path)
    get_result_from_durations(durations_output_path, analyzed_durations_path)

def run_performance_analysis_on_nightly(range_of_time, array_of_apk_path):
    for apk_path in array_of_apk_path:
        analyze_nightly_for_one_build(apk_path)

#def validate_args(args):

def main():
    args = argparse.ArgumentParser(description="")

    validate_args()

    range_of_time = 7

    array_of_apk_metadata = download_nightly_for_range(range_of_time)
    run_performance_analysis_on_nightly(range_of_time, array_of_apk_metadata)




