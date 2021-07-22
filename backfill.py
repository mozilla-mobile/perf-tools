import argparse
import urllib.request
import subprocess
import analyze_durations
import os
from pathlib import Path
from datetime import datetime, timedelta

DESCRIPTION = """ Allows to get startup performance metrics between two dates.
This can backfill numbers for either daily nightlys or for two commits.
"""

NIGHTLY_BASE_URL = "https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/mobile.v2.fenix.nightly.{date}.latest.armeabi-v7a/artifacts/public%2Fbuild%2Farmeabi-v7a%2Ftarget.apk"
BACKFILL_DIR = "backfill_output"
DURATIONS_OUTPUT_FILE_TEMPLATE = "durations_for_{apk}.txt"
ANALYZED_DURATIONS_FILE_TEMPLATE = "{apk_name}_perf_results.txt"

KEY_NAME = "name"
KEY_DATETIME = "date"

DATETIME_FORMAT = "%Y.%m.%d"

def prase_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument("path_to_startup_script", help="Path to the measure_start_up.py script needed to gather startup performance metrics")
    parser.add_argument("package_id", help="Package id associated with the apk to install / uninstall")
    parser.add_argument("start", type=lambda date: datetime.strptime(date, DATETIME_FORMAT), help="Date to start the backfill")
    parser.add_argument("-ed", "--enddate", type=lambda date: datetime.strptime(date, DATETIME_FORMAT), help="""end time for this script to backfill. If none is
    indicated, it wil default to the current date""")
    parser.add_argument("-rp","--repository_path", help="Path to the repository where the commits will be gotten from")
    parser.add_argument("-t", "--type", required=True, choices=["nightly","commits"], help="The type of system the backfill should run performance analysis on")
    parser.add_argument("-cl", "--cleanup", choices=[True, False], default=False, help="Remove all apks downloaded since they can takeup lots of space")
    return parser.parse_args()

def fetch_nightly(download_date):
    download_date_string = datetime.strftime(download_date,DATETIME_FORMAT)
    nightly_url = NIGHTLY_BASE_URL.format(date=download_date_string)
    filename = "nightly_" + download_date_string.replace(".","_") + ".apk"
    #TODO: Could add build type, architecture, etc...
    apk_metadata = {KEY_NAME: filename, KEY_DATETIME: download_date}
    try:
        urllib.request.urlretrieve(nightly_url, filename=filename)
    except urllib.error.HTTPError as err:
        apk_metadata = None
        if err.code == 404:
            print("\n\nThe apk for {date} is not available at this {url}".format(date=download_date,url=nightly_url))
    return apk_metadata

def get_date_array_for_range(startdate, enddate):
    date_array = []
    delta = (enddate - startdate).days + 1
    for i in range(delta):
        date_array.append(startdate + timedelta(days=i))
    return date_array

def download_nightly_for_range(array_of_dates):
    apk_metadata_array = []
    for date in array_of_dates:
        #TODO if file exist and no -f option
        apk_metadata = fetch_nightly(date)
        if apk_metadata is not None:
            apk_metadata_array.append(apk_metadata)
    return apk_metadata_array

def install_apk(apk_build_path):
    install_output = subprocess.run(["adb","install",apk_build_path], check=False, capture_output=True  )
    if len(install_output.stderr.decode('utf-8').strip()) == 0:
        return True
    else:
        print("""\n\n Something went wrong while installing the following apk:{apk} . The associated error message was:
        \n {error}""".format(apk= apk_build_path, error = install_output.stderr))
        return False

def uninstall_apk(package_id):
    uninstall_output = subprocess.run(["adb", "uninstall",package_id],check=False, capture_output=True  )
    if len(uninstall_output.stderr.decode('utf-8').strip()) != 0:
          print("""\n\n Something with the uninstalling {package_id} went wrong. The associated error message was:
        \n {error}""".format(package_id = package_id, error = uninstall_output.stderr.decode('utf-8').strip("\n")))


def run_measure_start_up_script(path_to_measure_start_up_script, durations_output_path):
    output = subprocess.run([path_to_measure_start_up_script,"nightly","cold_view_nav_start",durations_output_path ], capture_output=True, check=False)

    if output.stderr is not None:
        print(output.stderr.decode('utf-8').strip("\n"))

def analyze_nightly_for_one_build(package_id, path_to_measure_start_up_script, apk_metadata):
    uninstall_apk(package_id)

    was_install_successfull = install_apk(apk_metadata[KEY_NAME])

    if was_install_successfull:
        Path(BACKFILL_DIR).mkdir(parents=True, exist_ok=True)

        apk_name = apk_metadata[KEY_NAME].split(".")[0]

        #TODO fix verify if file exist to have -f in this script
        durations_output_path= os.path.join(BACKFILL_DIR, DURATIONS_OUTPUT_FILE_TEMPLATE.format(apk=apk_name))
        analyzed_durations_path = os.path.join(BACKFILL_DIR, ANALYZED_DURATIONS_FILE_TEMPLATE.format(apk_name=apk_name))

        run_measure_start_up_script(path_to_measure_start_up_script, durations_output_path)
        get_result_from_durations(durations_output_path, analyzed_durations_path)
    else:
        print("Installation for the apk {apk} was unsuccessfull".format(apk= apk_metadata[KEY_NAME]))

def get_result_from_durations(start_up_durations_path, analyzed_path):
    try:
        filetype = analyze_durations.detect_filetype(start_up_durations_path)
        measurement_arr = filetype.read_from(start_up_durations_path)
        stats = analyze_durations.to_stats(measurement_arr)
        analyze_durations.save_output(stats, analyzed_path)
    except Exception:
        print("The file {file} doesn't exist, this is probably due to a failure in running the measure_start_up.py script for the apk with the according date".format(file = start_up_durations_path))

def run_performance_analysis_on_nightly(package_id, path_to_measure_start_up_script, array_of_apk_path):
    for apk_path in array_of_apk_path:
        analyze_nightly_for_one_build(package_id,path_to_measure_start_up_script, apk_path)


def cleanup(array_of_apk_path):
    for i in array_of_apk_path:
        subprocess.run(["rm", i[KEY_NAME]])

def main():
    args = prase_args()

    path_to_measure_start_up_script = args.path_to_startup_script
    package_id = args.package_id
    startdate = args.start
    enddate = args.enddate
    if args.enddate is None:
        enddate = datetime.now()

    if args.type == "commits" and args.fenix_path is None:
        raise Exception("Please provide the path to your fenix repository to be run this script with the commits option")

    array_of_dates = get_date_array_for_range(startdate,enddate)

    if args.type == "nightly":
        array_of_apk_metadata = download_nightly_for_range(array_of_dates)

    run_performance_analysis_on_nightly(package_id, path_to_measure_start_up_script, array_of_apk_metadata)

    if cleanup == True:
        cleanup(array_of_apk_metadata)

if __name__ == '__main__':
    main()