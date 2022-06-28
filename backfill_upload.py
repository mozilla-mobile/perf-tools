#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""A script to upload our backfill perf test data to grafana.
We use a standalone script because we may not wish to upload every
time we run backfill (e.g. when we identify regressions or test the system).
"""

import argparse
import ast
import backfill
from datetime import datetime
import json
import os
import subprocess
import sys
import re
import urllib

PATH_SECRETS = '.backfill_secrets.json'
SECRETS_KEY_AUTH = 'AUTH'

DBI = 'performance'
DBHOST = "hilldale-b40313e5.influxcloud.net"
URL = "https://{DBHOST}:8086/api/v2/write?bucket={DBI}&precision=s".format(DBHOST=DBHOST, DBI=DBI)

KEY_MEDIAN = 'median'
KEY_TIMESTAMP_DATETIME = 'apk_timestamp_datetime'
KEY_TIMESTAMP_EPOCH = 'apk_timestamp_epoch'

TEST_NAME_TO_DASHBOARD_METRIC = {
    # We hardcode the keys, rather than using constants, so we can preserve the dashboard names if
    # the test names change in measure_start_up.py.
    'cold_main_first_frame': 'backfill-cold-main-first-frame',
    'cold_view_nav_start': 'backfill-cold-view-nav-start',
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action="store_true")
    return parser.parse_args()


def get_secrets():
    with open(PATH_SECRETS) as f:
        secrets = json.load(f)
    assert secrets.get(SECRETS_KEY_AUTH), 'Please supply authorization token in {}'.format(PATH_SECRETS)
    return secrets


def get_device():
    proc = subprocess.run(['adb', 'shell', 'getprop', 'ro.product.model'], capture_output=True)
    if proc.returncode != 0:
        raise Exception(f'failed to get device:\n  {proc.stderr}')

    device = proc.stdout.strip()
    if device == b'SM-A515F':
        return 'samsung-a51'
    elif device == b'Moto G (5)':
        return 'moto-g5'
    else:
        raise AssertionError((f'Unknown device "{device}". If we expect this '
                              f'device to appear on the dashboards, please add '
                              f'it to the source code.'))


def prompt_for_device(device):
    '''Gets the model of the device that is currently plugged in and prompts
    the user if this is the one they want to upload for. We do it this way,
    rather than the command line argument, so we're less likely to mess it up.
    '''
    value = ''
    while value != 'y' and value != 'n':
        value = input(f'Found device {device}. Is this correct? (y/n) ')
        value = value.strip().lower()

    if value == 'n':
        print('Stopping upload at user prompt: please connect desired device.')
        sys.exit(1)
    elif value == 'y':
        pass  # Continue the upload
    else:
        raise AssertionError(f'Expected value y or n. Got {value}')


def find_perf_result_files_to_upload():
    return [os.path.join(backfill.BACKFILL_DIR, f) for f in os.listdir(backfill.BACKFILL_DIR)
            if f.endswith('-analysis.txt')]


def get_perf_results_to_upload(perf_result_file_paths):
    output_results = []
    for path in perf_result_file_paths:
        with open(path) as f:
            perf_result = ast.literal_eval(f.read())

        # Append the date to the object so it's easier to upload. Since we only record the date,
        # we set the time to a constant for consistency between uploads.
        #
        # Example file name: 0-nightly_2021_09_01-cold_main_first_frame-analyzed.txt
        date_str = re.search(r'(\d{4}_\d{2}_\d{2})', path).group(1)
        date = datetime.strptime(date_str + ' 12:00:01', '%Y_%m_%d %H:%M:%S')
        perf_result[KEY_TIMESTAMP_DATETIME] = date
        perf_result[KEY_TIMESTAMP_EPOCH] = round(date.timestamp())
        output_results.append(perf_result)
    return output_results


def upload(perf_result, auth_token, device, is_dry_run):
    date_str = perf_result[KEY_TIMESTAMP_DATETIME].strftime('%Y-%m-%d')

    def print_failure(e):
        print('Request for {date} failed:'.format(date=date_str), sys.stderr)
        if e:
            print(e, file=sys.stderr)

    # I think this data upload format is from prometheus:
    # https://prometheus.io/docs/instrumenting/exposition_formats/#comments-help-text-and-type-information
    #
    # But I don't know why we can upload seconds here when prometheus asks for ms.
    metric_name = TEST_NAME_TO_DASHBOARD_METRIC[perf_result[backfill.KEY_TEST_NAME]]
    req_data = '{metric},device={device},product={product} value={value} {timestamp}'.format(
        metric=metric_name,
        device=device,
        product=perf_result[backfill.KEY_PRODUCT] + '-nightly',  # we only support nightly currently
        value=perf_result[KEY_MEDIAN],
        timestamp=perf_result[KEY_TIMESTAMP_EPOCH],
    )
    headers = {'Authorization': auth_token}

    if is_dry_run:
        print('Would attempt to upload data for date {}:\n  {}'.format(date_str, req_data))
        return

    request = urllib.request.Request(url=URL, headers=headers, data=bytes(req_data, 'utf-8'))
    try:
        with urllib.request.urlopen(request) as res:
            res_body = res.read()
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print_failure(e)

    if 200 <= res.status < 300:
        print("Uploaded results for {date} {metric_name}".format(date=date_str, metric_name=metric_name))
    else:
        print_failure('Response for {date} {metric_name} was not HTTP success. Was {status}'.format(
                      date=date_str, metric_name=metric_name, status=res.status))


def main():
    args = parse_args()
    if args.dry_run:
        print("dry run selected: results will not be uploaded.")

    secrets = get_secrets()
    device = get_device()
    prompt_for_device(device)

    perf_result_file_paths = find_perf_result_files_to_upload()
    perf_results = get_perf_results_to_upload(perf_result_file_paths)
    for result in perf_results:
        upload(result, secrets[SECRETS_KEY_AUTH], device, args.dry_run)


if __name__ == '__main__':
    main()
