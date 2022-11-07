# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import urllib.request
import subprocess
import analyze_durations
import os
import sys
import measure_start_up
import time
from pathlib import Path
from measure_start_up import PROD_TO_CHANNEL_TO_PKGID, PROD_FENIX, PROD_FOCUS
from datetime import datetime, timedelta
from pathlib import Path

DESCRIPTION = """ Allows to get startup performance metrics between two dates.
This can backfill numbers for either daily nightlys or for two commits.
"""

BASE_URL_DICT = {}
BASE_URL_DICT[PROD_FENIX] = ("https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/"
                             "mobile.v2.fenix.nightly.{date}.latest.{architecture}/artifacts/"
                             "public%2Fbuild%2F{architecture}%2Ftarget.apk")
# Despite the URL including "unsigned", these are actually signed builds.
BASE_URL_DICT[PROD_FOCUS] = ("https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/"
                             "mobile.v2.focus-android.nightly.{date}.latest.{architecture}/artifacts/"
                             "public%2Fbuild%2Fapp-focus-{architecture}-nightly-unsigned.apk")
# See usage for why this exists.
BASE_URL_DICT[PROD_FOCUS + '-v2'] = ("https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/"
                                     "mobile.v2.focus-android.nightly.{date}.latest.{architecture}/artifacts/"
                                     "public%2Fbuild%2Ffocus%2F{architecture}%2Ftarget.apk")


BACKFILL_DIR = "backfill_output"

DURATIONS_OUTPUT_FILE_TEMPLATE = "{run_number}-{apk_name}-{test_name}-durations.txt"
ANALYZED_DURATIONS_FILE_TEMPLATE = "{run_number}-{apk_name}-{test_name}-analysis.txt"

BUILD_SRC_TASKCLUSTER = "taskclusterNightly"
BUILD_SRC_COMMITS = "commitsRange"
BUILD_SRC_ALL = [BUILD_SRC_TASKCLUSTER, BUILD_SRC_COMMITS]

KEY_NAME = "name"
KEY_PRODUCT = "product"
KEY_DATETIME = "date"
KEY_COMMIT = "commit"
KEY_ARCHITECTURE = "architecture"
KEY_TEST_NAME = "test_name"

DATETIME_FORMAT = "%Y.%m.%d"

MEASURE_START_UP_SCRIPT = "./measure_start_up.py"


def parse_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument("product", choices=[PROD_FENIX, PROD_FOCUS], help="the product to measure")

    # We try to match the argument ordering with measure_start_up.py.
    parser.add_argument("release_channel", choices=["nightly", "beta", "release", "debug"],
                        help="The firefox build to run performance analysis on")
    parser.add_argument("architecture", choices=["armeabi-v7a", "arm64-v8a"])
    parser.add_argument("build_source", choices=BUILD_SRC_ALL,
                        help="The type of system the backfill should run performance analysis on. The commitsRange" +
                        "will get commits between two commits")

    # I think this would be more natural as a positional, comma-separated list but argparse doesn't support it.
    parser.add_argument("--tests", nargs="+", choices=measure_start_up.TESTS, required=True,
                        help=("the test(s) to run: see `python3 measure_start_up.py --help` for details on the tests. "
                              "This flag should be specified once with space-separated arguments."))

    parser.add_argument("--startdate", type=lambda date: datetime.strptime(date, DATETIME_FORMAT),
                        help="Date to start the backfill")
    parser.add_argument("--enddate", type=lambda date: datetime.strptime(date, DATETIME_FORMAT),
                        default=datetime.now(),
                        help="end date to backfill until.If empty, default will be the current date")
    parser.add_argument("--startcommit", help="Oldest commit to build.")
    parser.add_argument("--endcommit", help="Last commit to run performance analysis")

    parser.add_argument("--git_remote_name",  help="If this needs to run on a remote repository, pass the name here")
    parser.add_argument("--repository_to_test_path",
                        help="Path to the repository where the commits will be gotten from")
    parser.add_argument("-c", "--cleanup", action="store_true",
                        help="Remove all apks downloaded since they can takeup lots of space")

    return parser.parse_args()


def get_nightly_url(download_date, download_date_str, product, architecture):
    # The url format changed for builds after this date.
    if product == PROD_FOCUS and download_date >= datetime(2021, 11, 5):
        product += '-v2'
    return BASE_URL_DICT[product].format(date=download_date_str, architecture=architecture)


def fetch_nightly(download_date, architecture, product):
    download_date_string = datetime.strftime(download_date, DATETIME_FORMAT)
    nightly_url = get_nightly_url(download_date, download_date_string, product, architecture)
    filename = "{}_nightly_{}_{}.apk".format(product, architecture, download_date_string.replace(".", "_"))
    print("Fetching {}...".format(filename), end="", flush=True)
    try:
        urllib.request.urlretrieve(nightly_url, filename=filename)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            print("\n\nThe apk for {date} is not available at this {url}".format(date=download_date, url=nightly_url),
                  file=sys.stderr)
        return None

    print(" Success.")

    return {KEY_NAME: filename, KEY_DATETIME: download_date, KEY_COMMIT: "", KEY_ARCHITECTURE: architecture,
            KEY_PRODUCT: product}


def get_date_array_for_range(startdate, enddate):
    delta_dates = (enddate - startdate).days + 1
    return [startdate + timedelta(days=i) for i in range(delta_dates)]


def download_nightly_for_range(array_of_dates, architecture, product):
    # TODO if file exist and no -f option
    apk_metadata_array = [fetch_nightly(date, architecture, product) for date in array_of_dates]
    return [e for e in apk_metadata_array if e is not None]


def install_apk(apk_build_path):
    install_proc = subprocess.run(["adb", "install", apk_build_path], check=False, capture_output=True)
    if install_proc.returncode != 0:
        print(("\nUnable to install: {apk}. The associated error message was:\n"
               "{error}".format(apk=apk_build_path, error=install_proc.stderr.decode('utf-8'))),
              file=sys.stderr)
        return False
    return True


def uninstall_apk(package_id):
    uninstall_proc = subprocess.run(["adb", "uninstall", package_id], check=False, capture_output=True)
    if uninstall_proc.returncode != 0:
        print(("\nUnable to uninstall {package_id}. The associated error message was:\n"
               "{error}".format(package_id=package_id, error=uninstall_proc.stderr.decode('utf-8'))),
              file=sys.stderr)


def clear_app_data(package_id):
    clear_proc = subprocess.run(['adb', 'shell', 'pm', 'clear', package_id], check=False, capture_output=True)
    if clear_proc.returncode != 0:
        print(("\nUnable to clear app data for {package_id}. The associated error message was:\n"
               "{error}".format(package_id=package_id, error=clear_proc.stderr.decode('utf-8'))),
              file=sys.stderr)


def maybe_skip_onboarding(package_id, test_name, product):
    # We skip onboarding for focus in measure_start_up.py because it's stateful and needs to be called
    # for every cold start intent.
    if product == PROD_FOCUS:
        return

    # Onboarding only visibly gets in the way of our MAIN test results.
    if product == PROD_FOCUS or \
            test_name not in {measure_start_up.TEST_COLD_MAIN_FF, measure_start_up.TEST_COLD_MAIN_RESTORE}:
        return

    # This sets mutable state so we only need to pass this flag once, before we start the actual test.
    start_proc = subprocess.run(['adb', 'shell', 'am', 'start-activity', '-W',
                                 '-a', 'android.intent.action.MAIN',
                                 '--ez', 'performancetest', 'true',  # Skip onboarding.
                                 '-n' '{}/org.mozilla.fenix.App'.format(package_id)],
                                check=False, capture_output=True)
    if start_proc.returncode != 0:
        print(("\nUnable to skip onboarding. The associated error message was:\n"
               "{error}".format(error=start_proc.stderr.decode('utf-8'))),
              file=sys.stderr)

    time.sleep(4)  # ensure skip onboarding call has time to propagate.


def run_measure_start_up_script(path_to_measure_start_up_script, durations_output_path, build_type, test_name, product):
    subprocess.run([path_to_measure_start_up_script, "--product=" + product, build_type, test_name,
                    # The iteration count is chosen manually, through trial-and-error,
                    # to minimize both execution time and noise.
                    '--iter-count', '30',
                    durations_output_path], stdout=subprocess.PIPE, check=False)


def analyze_nightly_for_one_build(index, package_id, path_to_measure_start_up_script, apk_metadata, build_type, tests,
                                  product):
    uninstall_apk(package_id)

    print("Installing {}...".format(apk_metadata[KEY_NAME]))
    was_install_successful = install_apk(apk_metadata[KEY_NAME])
    if was_install_successful:
        Path(BACKFILL_DIR).mkdir(parents=True, exist_ok=True)

        apk_name = apk_metadata[KEY_NAME].split(".")[0]

        for test_name in tests:
            print("Running {test_name} on {apk_name}...".format(test_name=test_name, apk_name=apk_name))

            clear_app_data(package_id)  # Don't maintain state between tests.
            maybe_skip_onboarding(package_id, test_name, product)

            # TODO fix verify if file exist to have -f in this script
            durations_output_path = os.path.join(BACKFILL_DIR, DURATIONS_OUTPUT_FILE_TEMPLATE.format(
                run_number=index, apk_name=apk_name, test_name=test_name))
            analyzed_durations_path = os.path.join(BACKFILL_DIR, ANALYZED_DURATIONS_FILE_TEMPLATE.format(
                run_number=index, apk_name=apk_name, test_name=test_name))
            run_measure_start_up_script(path_to_measure_start_up_script, durations_output_path, build_type, test_name,
                                        product)
            get_result_from_durations(durations_output_path, analyzed_durations_path, test_name, product)


def get_result_from_durations(start_up_durations_path, analyzed_path, test_name, product):
    try:
        filetype = analyze_durations.detect_filetype(start_up_durations_path)
    except FileNotFoundError:
        print(("The file {file} doesn't exist, this is probably due to a failure in running"
               "the measure_start_up.py for the apk with the according date").format(file=start_up_durations_path),
              file=sys.stderr)
        return

    measurement_arr = filetype.read_from(start_up_durations_path)
    stats = analyze_durations.to_stats(measurement_arr)
    stats[KEY_TEST_NAME] = test_name
    stats[KEY_PRODUCT] = product
    analyze_durations.save_output(stats, analyzed_path)


def run_performance_analysis_on_nightly(package_id, path_to_measure_start_up_script, array_of_apk_path, build_type,
                                        tests, product):
    for idx, apk_path in enumerate(array_of_apk_path):
        analyze_nightly_for_one_build(idx, package_id, path_to_measure_start_up_script, apk_path, build_type, tests,
                                      product)


def fetch_repository(repository_path, remote_name):
    remote_repo_name = "upstream" if len(remote_name) == 0 else remote_name

    fetch_proc = subprocess.run(["git", "fetch", remote_repo_name], cwd=repository_path, capture_output=True)

    if fetch_proc.returncode != 0:
        print(("\n\nSomething went wrong while fetching this repostirory: {repo} . The associated error message was:"
               "\n\n {error}".format(repo=repository_path, error=fetch_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)


def get_all_commits_in_commits_range(start_commit, end_commit, repository_path):
    commit_proc = subprocess.run(
        ["git", "rev-list", "--ancestry-path", start_commit + "^.." + end_commit],
        cwd=repository_path, capture_output=True, text=True)

    if commit_proc.returncode != 0:
        print(("\n\nSomething went wrong while checking out this commit range: {start}..{end}" +
               "The associated error message was:\n\n {error}".format(
                start=start_commit, end=end_commit, error=commit_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)

    return [e for e in commit_proc.stdout.split("\n") if e]


def clean_project(repository_path):
    clean_proc = subprocess.run(["./gradlew", "clean"], cwd=repository_path, capture_output=True)

    if clean_proc.returncode != 0:
        print(("\n\nSomething went wrong while ./gradlew clean. The associated error message was:"
               "\n\n {error}".format(error=checkout_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)
        return


def build_apk_for_commit(hash, repository_path, build_type):
    checkout_proc = subprocess.run(["git", "checkout", hash], cwd=repository_path, capture_output=True)

    if checkout_proc.returncode != 0:
        print(("\n\nSomething went wrong while checking out this commit: {commit} . The associated error message was:"
               "\n\n {error}".format(commit=hash, error=checkout_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)
        return

    assemble_proc = subprocess.run(["./gradlew", "assemble"+build_type], cwd=repository_path, capture_output=True)

    if assemble_proc.returncode != 0:
        print(("\n\nSomething went wrong while assembling this build: {build} . The associated error message was:"
               "\n\n {error}".format(build=build_type, error=checkout_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)


def build_apk_path_string(repository_path, build_type, phone_architecture):
    apk_name = "app-{phone_arch}-{build_type}.apk".format(phone_arch=phone_architecture, build_type=build_type)
    build_apk_destination = os.path.join(repository_path, "app", "build", "outputs", "apk", build_type, apk_name)
    return build_apk_destination


def move_apk_to_cwd(apk_path, commit_hash):
    new_apk_name = "apk_commit_" + commit_hash + ".apk"
    proc = subprocess.run(["mv", apk_path, new_apk_name])
    if proc.returncode != 0:
        print(("\n\nSomething went wrong while moving the built apk: {apk} . The associated error message was:"
               "\n\n {error}".format(apk=apk_path, error=proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)
    return new_apk_name


def build_apks_for_commits(
        start_commit=None, end_commit=None, repository_path=None,
        build_type=None, architecture=None, remote_name=""):
    apk_metadata_array = []

    fetch_repository(repository_path, remote_name)
    array_of_commit_hash = get_all_commits_in_commits_range(start_commit, end_commit, repository_path)
    clean_project(repository_path)

    numer_of_commits = len(array_of_commit_hash)
    for index, commit in enumerate(array_of_commit_hash):
        print(f'##### Trying to build {index+1} of {numer_of_commits} Actual commit {commit} #####')
        new_apk_name = "apk_commit_" + commit + ".apk"
        apk_for_commit_already_exists = Path(new_apk_name).exists()

        if not apk_for_commit_already_exists:
            build_apk_for_commit(commit, repository_path, build_type)
            built_apk_name = build_apk_path_string(repository_path, build_type, architecture)
            new_apk_name = move_apk_to_cwd(built_apk_name, commit)
        else:
            print(f'     SKIPED build for commit {commit}, apk already exists')

        apk_metadata_array.append({
            KEY_NAME: new_apk_name,
            KEY_DATETIME: "",
            KEY_COMMIT: commit,
            KEY_ARCHITECTURE: architecture})
    return apk_metadata_array


def cleanup(array_of_apk_path):
    for i in array_of_apk_path:
        subprocess.run(["rm", i[KEY_NAME]])


def validate_args(args):
    if args.product == PROD_FOCUS and args.build_source == BUILD_SRC_COMMITS:
        raise Exception("Focus with commits is not currently supported")

    if args.build_source == BUILD_SRC_TASKCLUSTER and args.startdate is None:
        raise Exception("A start date is required to run using taskcluster builds")
    if args.build_source == BUILD_SRC_COMMITS and args.repository_to_test_path is None:
        raise Exception("Provide the path to your fenix repository to run this script with the commits option")
    if args.build_source == BUILD_SRC_COMMITS and not args.startcommit and not args.endcommit:
        raise Exception("Running backfill with commits between two commits requires a start and end commit")


def main():
    args = parse_args()
    validate_args(args)

    if args.build_source == BUILD_SRC_TASKCLUSTER:
        array_of_dates = get_date_array_for_range(args.startdate, args.enddate)
        array_of_apk_metadata = download_nightly_for_range(array_of_dates, args.architecture, args.product)
    elif args.build_source == BUILD_SRC_COMMITS:
        array_of_apk_metadata = build_apks_for_commits(
            start_commit=args.startcommit,
            end_commit=args.endcommit,
            repository_path=args.repository_to_test_path,
            build_type=args.release_channel,
            architecture=args.architecture,
            remote_name=args.git_remote_name if args.git_remote_name else "")

    run_performance_analysis_on_nightly(
        PROD_TO_CHANNEL_TO_PKGID[args.product][args.release_channel],
        MEASURE_START_UP_SCRIPT,
        array_of_apk_metadata,
        args.release_channel,
        args.tests,
        args.product)

    if args.cleanup is True:
        cleanup(array_of_apk_metadata)


if __name__ == '__main__':
    main()
