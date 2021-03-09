#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
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


def parse_args():
    parser = argparse.ArgumentParser(description=DESC, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="path to a file with duration measurements separated by newlines")
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


def to_stats(measurements_arr):
    return {
        'max': max(measurements_arr),
        'mean': stat.mean(measurements_arr),
        'median': stat.median(measurements_arr),
        'replicates': measurements_arr
    }


def print_github_table_header():
    print('|Iteration desc|mean|median|max|')
    print('|-|-|-|-|')


def to_github_table_row(stats):
    return '|todo-iteration-name|{}|{}|{}|'.format(stats['mean'], stats['median'], stats['max'])


def main():
    args = parse_args()

    if args.print_github_table_header:
        print_github_table_header()
        exit(0)

    measurement_arr = read_from_file_separated_by_newlines(args.path)
    stats = to_stats(measurement_arr)

    if args.print_github_table_row:
        print(to_github_table_row(stats))
    else:
        pprint(stats, compact=True)


if __name__ == '__main__':
    main()
