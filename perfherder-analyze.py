#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TODO: explain me.
"""

import fileinput
import json
import os
import statistics
import sys
from argparse import ArgumentParser
from matplotlib import pyplot
from pprint import pprint

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--save-dir', help='place to save results')
    parser.add_argument('--save-id', help='an identifier to save the files as')
    return parser.parse_args()


def validate_args(args):
    if bool(args.save_dir) ^ bool(args.save_id):
        raise Exception('if --save-dir is specified, --save-id must be specified too or vice versa')


def get_perfherder_data(stdin):
    """
    Example data:
    PERFHERDER_DATA: {"suites": [{"name": "VIEW", "type": "pageload", "value": 2815.9, "unit": "ms", "extraOptions": [], "lowerIsBetter": true, "alertThreshold": 2.0, "shouldAlert": false, "subtests": [{"name": "browserScripts.pageinfo.processLaunchToNavStart", "replicates": [3010, 2869, 2777, 2718, 2860, 2893, 2821, 2774, 2714, 2723], "lowerIsBetter": true, "value": 2815.9, "unit": "ms", "shouldAlert": false}]}], "framework": {"name": "browsertime"}, "application": {"name": "fenix"}}
    """
    prefix = 'PERFHERDER_DATA: '
    matching_lines = [e for e in stdin if e.startswith(prefix)]
    if len(matching_lines) != 1:
        raise Exception('Expected exactly one line to start with "{}"'.format(prefix))

    match = matching_lines[0]
    json_str = match[len(prefix):]
    return json.loads(json_str)


def get_perfherder_replicates(raw_data):
    suite = raw_data['suites'][0]
    #mean = suite['value']
    return suite['subtests'][0]['replicates']


def analyze_replicates(replicates):
    return {
        'test': 'perftest-VIEW',
        'replicates': replicates,
        'mean': statistics.mean(replicates),
        'median': statistics.median(replicates)
    }


def graph(analysis, save_path):
    # Relies on previous method to ensure save_path dirs exists.
    replicates = analysis['replicates']
    #pyplot.plot(range(len(replicates)), replicates)
    y = [5 for _ in replicates]
    pyplot.scatter(replicates, y)
    if save_path:
        pyplot.savefig(save_path + '-graph.pdf')
    pyplot.show()


def save_analysis(analysis, save_dir, save_path):
    os.makedirs(save_dir, exist_ok=True)

    path = save_path + '-analysis.txt'
    with open(path, 'w') as f:
        pprint(analysis, stream=f, compact=True)
    # TODO: save graph


def main():
    args = parse_args()
    validate_args(args)

    raw_data = get_perfherder_data(sys.stdin)
    replicates = get_perfherder_replicates(raw_data)
    analysis = analyze_replicates(replicates)

    save_path = None
    if args.save_dir and args.save_id:
        save_path = os.path.join(args.save_dir, args.save_id)
        save_analysis(analysis, args.save_dir, save_path)
    pprint(analysis, compact=True)
    graph(analysis, save_path)


if __name__ == '__main__':
    main()
