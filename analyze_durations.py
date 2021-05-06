#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import ast
import json
import os
import re
import statistics as stat
import sys
from enum import Enum, auto
from pprint import pprint

DESC = """Provides statistics relevant to performance analysis on the given duration
measurements such as the mean, median, and max values. Sample output:

{'max': 2415.0,
 'mean': 2187.92,
 'median': 2141.0,
 'min': 2101.0,
 'replicate_count': 50,
 'replicates': [2116.0, 2212.0, 2145.0, ..., 2391.0, 2195.0]}

See the `path` argument for supported file formats.
"""

LOGCAT_MATCH_STR = 'average '
LOGCAT_EXPECTED_FORMAT = '2020-05-04 15:15:50.340 10845-10845/? E/lol: average 37'


def parse_args():
    parser = argparse.ArgumentParser(description=DESC, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("path", help="""path to a file with duration measurements. The following formats are supported:
- durations separated by newlines
- perfherder-data-json output from mozperftest VIEW
- logcat where some lines have a logged value of 'average <duration>'
- the output of this script""")

    parser.add_argument("-o", "--output-safe", help="""writes the output to the given path, in addition to printing.
This operation is safe (non-destructive): if the path already exists, the script will abort.
This is useful to avoid accidentally deleting results.""")

    parser.add_argument("--graph", action="store_true", help="displays a graph of the replicates, in addition to printing the output. Requires matplotlib (from the venv requirements)")

    parser.add_argument(
        "--print-github-table-header", action="store_true",
        help="prints the input-agnostic header for --print-github-table-row args and exits. " +
        "the path is still required to ease the implementation requirements"
    )
    parser.add_argument(
        "--print-github-table-row", action="store_true", help="prints the result formatted as a GitHub table row"
    )
    return parser.parse_args()


def detect_filetype(path):
    with open(path) as f:
        contents = f.read()

    if contents.startswith('{"suites":'):
        return InputFileType.PERFHERDER_JSON
    elif contents.startswith("{'"):
        return InputFileType.SCRIPT_OUTPUT
    elif re.match('^\d+-\d+', contents):
        return InputFileType.LOGCAT
    else:
        return InputFileType.NEWLINES


def read_from_file_separated_by_newlines(path):
    with open(path) as f:
        contents = f.read()
    return [float(r) for r in contents.split('\n') if r]  # trailing if is used to remove empty lines.


def read_from_perfherder_json(path):
    with open(path) as f:
        contents = json.load(f)

    # Hard-coded to paths for perftest VIEW.
    return [float(e) for e in contents['suites'][0]['subtests'][0]['replicates']]


def read_from_output(path):
    with open(path) as f:
        contents = ast.literal_eval(f.read())
    return contents['replicates']


def read_from_logcat_file(path):
    measurements = []
    with open(path) as f:
        for line in f:
            # The message will be after the last colon because we demand a certain formatting.
            message_text = line[line.rfind(': ') + 2:]  # +2 to move past ': '.

            if message_text and message_text.startswith(LOGCAT_MATCH_STR):
                measurements.append(float(message_text[len(LOGCAT_MATCH_STR):]))

    if len(measurements) == 0:
        print('WARN: no lines matched. expected format like:\n    {}'.format(LOGCAT_EXPECTED_FORMAT))
    return measurements


def to_stats(measurements_arr):
    return {
        'max': max(measurements_arr),
        'mean': stat.mean(measurements_arr),
        'median': stat.median(measurements_arr),
        'min': min(measurements_arr),
        'replicate_count': len(measurements_arr),
        'replicates': measurements_arr,
    }


def print_github_table_header():
    print('|Iteration desc|mean|median|max|')
    print('|-|-|-|-|')


def to_github_table_row(stats):
    return '|todo-iteration-name|{}|{}|{}|'.format(stats['mean'], stats['median'], stats['max'])


def save_output(stats, path):
    if os.path.exists(path):
        raise Exception('path specified by --output-safe/-o already ' +
        'exists: aborting to prevent accidental overwrites. Use stream ' +
        'redirection operators for intentional overwriting.')

    with open(path, 'x') as f:
        print_stats(stats, f)

    print('Saved output to path: {}'.format(path))
    print('Also printing to stdout...\n')


def print_stats(stats, stream=None):
    if not stream:
        stream = sys.stdout
    pprint(stats, compact=True, stream=stream)


def graph(stats):
    from matplotlib import pyplot as plt
    replicates = stats['replicates']
    replicate_number = range(len(replicates))
    plt.xlabel('Iteration number')
    plt.ylabel('Duration')
    plt.scatter(replicate_number, replicates)
    plt.show()


class InputFileType(Enum):
    NEWLINES = auto()
    PERFHERDER_JSON = auto()
    SCRIPT_OUTPUT = auto()
    LOGCAT = auto()
    def read_from(self, path):
        if self is InputFileType.NEWLINES: return read_from_file_separated_by_newlines(path)
        elif self is InputFileType.PERFHERDER_JSON: return read_from_perfherder_json(path)
        elif self is InputFileType.SCRIPT_OUTPUT: return read_from_output(path)
        elif self is InputFileType.LOGCAT: return read_from_logcat_file(path)
        raise RuntimeError('Unknown input type: {}'.format(self))


def main():
    args = parse_args()

    if args.print_github_table_header:
        print_github_table_header()
        exit(0)

    filetype = detect_filetype(args.path)
    measurement_arr = filetype.read_from(args.path)
    stats = to_stats(measurement_arr)

    # Called before printing so if we abort, it's clearer to the user there was an error.
    if args.output_safe:
        save_output(stats, args.output_safe)

    if args.print_github_table_row:
        print(to_github_table_row(stats))
    else:
        print_stats(stats)

    if args.graph:
        graph(stats)


if __name__ == '__main__':
    main()
