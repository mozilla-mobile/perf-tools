#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import ast
import json
import statistics as stat
from pprint import pprint

DESC = """Provides statistics relevant to performance analysis on the given duration
measurements such as the mean, median, and max values. Sample output:

{'max': 10.0, 'mean': 5.0, 'median': 4.5, 'replicates': [1.0, 5.0, 10.0, 4.0]}

The provided file should contain duration measurements be separated by newlines.
For example, its contents might be:

846
854
844
"""

LOGCAT_MATCH_STR = 'average '
LOGCAT_EXPECTED_FORMAT = '2020-05-04 15:15:50.340 10845-10845/? E/lol: average 37'


def parse_args():
    parser = argparse.ArgumentParser(description=DESC, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("path", help="path to a file with duration measurements separated by newlines")

    parser.add_argument("--from-logcat", action="store_true", help="""reads a file with lines from logcat instead of durations separated by newlines.
The logcat message must be \"average <value>\": other log values such as tags are ignored. For example:

{}""".format(LOGCAT_EXPECTED_FORMAT))
    parser.add_argument("--from-perfherder", action="store_true", help="reads the perfherder-data.json output by mozperftest VIEW")
    parser.add_argument("--from-output", action="store_true", help="reads the output of this script: useful for drawing a graph or updating output from older versions of this script to newer versions")

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


def graph(stats):
    from matplotlib import pyplot as plt
    replicates = stats['replicates']
    replicate_number = range(len(replicates))
    plt.xlabel('Iteration number')
    plt.ylabel('Duration')
    plt.scatter(replicate_number, replicates)
    plt.show()


def main():
    args = parse_args()

    if args.print_github_table_header:
        print_github_table_header()
        exit(0)

    if args.from_logcat:
        measurement_arr = read_from_logcat_file(args.path)
    elif args.from_perfherder:
        measurement_arr = read_from_perfherder_json(args.path)
    elif args.from_output:
        measurement_arr = read_from_output(args.path)
    else:  # default operation: newline file format
        measurement_arr = read_from_file_separated_by_newlines(args.path)
    stats = to_stats(measurement_arr)

    if args.print_github_table_row:
        print(to_github_table_row(stats))
    else:
        pprint(stats, compact=True)

    if args.graph:
        graph(stats)


if __name__ == '__main__':
    main()
