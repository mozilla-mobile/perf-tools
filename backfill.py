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
KEY_COMMIT = "commit"
KEY_ARCHITECTURE = "architecture"

DATETIME_FORMAT = "%Y.%m.%d"

FENIX_CHANNEL_TO_PKG = {
    'nightly': 'org.mozilla.fenix',
    'beta': 'org.mozilla.firefox.beta',
    'release': 'org.mozilla.firefox',
    'debug': 'org.mozilla.fenix.debug'
}


def parse_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument("path_to_startup_script",
                        help="Path to the measure_start_up.py script needed to gather startupperformance metrics")
    parser.add_argument("release_channel", choices=["nightly", "beta", "release", "debug"],
                        help="The firefox build to run performance analysis on")
    parser.add_argument("architecture", choices=["armeabi-v7a", "arm64-v8a"])
    parser.add_argument("-t", "--type", required=True, choices=["nightly", "commitsDate", "commitsRange"],
                        help="The type of system the backfill should run performance analysis on. commitsDate option" +
                        "will get commits between two dates whereas the commitsRange will get commits between two" +
                        "commits")
    parser.add_argument("--startdate", type=lambda date: datetime.strptime(date, DATETIME_FORMAT),
                        help="Date to start the backfill")
    parser.add_argument("--enddate", type=lambda date: datetime.strptime(date, DATETIME_FORMAT),
                        default=datetime.now(),
                        help="end date to backfill until.If empty, default will be the current date")
    parser.add_argument("--startcommit", help="Oldest commit to build.")
    parser.add_argument("--endcommit", help="Last commit to run performance analysis")
    parser.add_argument("--repo_branch",  help="Branch to run this script on.")
    parser.add_argument("--git_remote_name",  help="If this needs to run on a remote repository, pass the name here")
    parser.add_argument("-r", "--repository_path",
                        help="Path to the repository where the commits will be gotten from")
    parser.add_argument("-c", "--cleanup", action="store_true",
                        help="Remove all apks downloaded since they can takeup lots of space")

    return parser.parse_args()


def fetch_nightly(download_date, architecture):
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
    return {KEY_NAME: filename, KEY_DATETIME: download_date, KEY_COMMIT: "", KEY_ARCHITECTURE: architecture}


def get_date_array_for_range(startdate, enddate):
    delta_dates = (enddate - startdate).days + 1
    return [startdate + timedelta(days=i) for i in range(delta_dates)]


def download_nightly_for_range(array_of_dates, architecture):
    # TODO if file exist and no -f option
    apk_metadata_array = [fetch_nightly(date, architecture) for date in array_of_dates]
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


def run_measure_start_up_script(path_to_measure_start_up_script, durations_output_path, build_type):
    subprocess.run([path_to_measure_start_up_script, build_type, "cold_view_nav_start", durations_output_path],
                   stdout=subprocess.PIPE, check=False)


def analyze_nightly_for_one_build(package_id, path_to_measure_start_up_script, apk_metadata, build_type):
    uninstall_apk(package_id)

    was_install_successful = install_apk(apk_metadata[KEY_NAME])
    if was_install_successful:
        Path(BACKFILL_DIR).mkdir(parents=True, exist_ok=True)

        apk_name = apk_metadata[KEY_NAME].split(".")[0]

        # TODO fix verify if file exist to have -f in this script
        durations_output_path = os.path.join(BACKFILL_DIR, DURATIONS_OUTPUT_FILE_TEMPLATE.format(apk=apk_name))
        analyzed_durations_path = os.path.join(BACKFILL_DIR, ANALYZED_DURATIONS_FILE_TEMPLATE.format(apk_name=apk_name))

        run_measure_start_up_script(path_to_measure_start_up_script, durations_output_path, build_type)
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


def run_performance_analysis_on_nightly(package_id, path_to_measure_start_up_script, array_of_apk_path, build_type):
    for apk_path in array_of_apk_path:
        analyze_nightly_for_one_build(package_id, path_to_measure_start_up_script, apk_path, build_type)


def checkout_repository_to_correct_branch(repository_path, branch, remote_name):
    remote_repo_name = "upstream" if len(remote_name) == 0 else remote_name
    branch = "main" if len(branch) == 0 else branch

    fetch_proc = subprocess.run(["git", "fetch", remote_repo_name], cwd=repository_path, capture_output=True)
    checkout_proc = subprocess.run(["git", "checkout", remote_repo_name + "/" + branch],
                                   cwd=repository_path, capture_output=True)

    if fetch_proc.returncode != 0:
        print(("\n\nSomething went wrong while fetching this repostirory: {repo} . The associated error message was:"
               "\n\n {error}".format(repo=repository_path, error=fetch_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)

    elif checkout_proc.returncode != 0:
        print(("\n\nSomething went wrong while checking out this branch: {br} . The associated error message was:"
               "\n\n {error}".format(br=branch, error=checkout_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)


def get_commits_for_date_range(startdate, enddate, repository_path):
    commit_proc = subprocess.run(
        ["git", "log", "--since={start}".format(start=startdate),
         "--until={end}".format(end=enddate), "--pretty=format:'%H'"],
        cwd=repository_path, capture_output=True, text=True).stdout

    if commit_proc.returncode != 0:
        print(("\n\nSomething went wrong while checking out this commit range: {start}..{end}" +
               "The associated error message was:\n\n {error}".format(
                start=startdate, end=enddate, error=commit_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)

    commit_string = proc.replace("'", "")
    return commit_string.split("\n")


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


def build_apk_for_commit(hash, repository_path, build_type):
    checkout_proc = subprocess.run(["git", "checkout", hash], cwd=repository_path, capture_output=True)

    if checkout_proc.returncode != 0:
        print(("\n\nSomething went wrong while checking out this commit: {commit} . The associated error message was:"
               "\n\n {error}".format(commit=hash, error=checkout_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)

    assemble_proc = subprocess.run(["./gradlew", "assemble"+build_type], cwd=repository_path, capture_output=True)

    if assemble_proc.returncode != 0:
        print(("\n\nSomething went wrong while assembling this build: {build} . The associated error message was:"
               "\n\n {error}".format(build=build_type, error=checkout_proc.stderr.decode('utf-8').strip("\n"))),
              file=sys.stderr)


def build_apk_path_string(repository_path, build_type, phone_architecture):
    apk_name = "app-" + phone_architecture + "-" + build_type + ".apk"
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
        startdate=None, enddate=None, start_commit=None, end_commit=None, repository_path=None,
        build_type=None, architecture=None, branch="", remote_name=""):
    apk_metadata_array = []

    checkout_repository_to_correct_branch(repository_path, branch, remote_name)

    if startdate is None:
        array_of_commit_hash = get_all_commits_in_commits_range(start_commit, end_commit, repository_path)
    else:
        array_of_commit_hash = get_commits_for_date_range(startdate, enddate, repository_path)
    for commit in array_of_commit_hash:
        build_apk_for_commit(commit, repository_path, build_type)
        built_apk_name = build_apk_path_string(repository_path, build_type, architecture)
        new_apk_name = move_apk_to_cwd(built_apk_name, commit)
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
    if args.type == "commits" and args.fenix_path is None:
        raise Exception("Provide the path to your fenix repository to run this script with the commits option")
    if args.type == "commitsDate" and not args.startdate:
        raise Exception("Running backfill with commits between two date requires a start date")
    if args.type == "commitsRange" and not args.startcommit and not args.endcommit:
        raise Exception("Running backfill with commits between two commits requires a start and end commit")
    if (args.type == "commitsRange" or args.type == "commitsDate") and not args.repository_path:
        raise Exception("Running backfill with any commits option " +
                        "requires a path to a repository where git can be used")
    if (args.type == "commitsRange" or args.type == "commitsDate") and not args.build_type:
        raise Exception("Running backfill with any commits option requires a built type")


def main():
    args = parse_args()

    validate_args(args)

    if args.type == "nightly":
        array_of_dates = get_date_array_for_range(args.startdate, args.enddate)
        array_of_apk_metadata = download_nightly_for_range(array_of_dates, args.architecture)
    elif args.type == "commitsDate":
        array_of_apk_metadata = build_apks_for_commits(
            startdate=args.startdate,
            enddate=args.enddate,
            repository_path=args.repository_path,
            build_type=args.build_type,
            architecture=args.architecture,
            branch=args.branch if args.branch else "",
            remote_name=args.git_remote_name if args.git_remote_name else "")
    else:
        array_of_apk_metadata = build_apks_for_commits(
            start_commit=args.startcommit,
            end_commit=args.endcommit,
            repository_path=args.repository_path,
            build_type=args.build_type,
            architecture=args.architecture,
            branch=args.branch if args.branch else "",
            remote_name=args.git_remote_name if args.git_remote_name else "")

    run_performance_analysis_on_nightly(
        FENIX_CHANNEL_TO_PKG[args.build_type],
        args.path_to_startup_script,
        array_of_apk_metadata,
        args.build_type)

    if args.cleanup is True:
        cleanup(array_of_apk_metadata)


if __name__ == '__main__':
    main()
