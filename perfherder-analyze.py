#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TODO: explain me.
Typical run:
    cat [file-with-array-from-fnprms|perfherder_data line] | ../perf-tools/perfherder-analyze.py [--fnprms] --save-dir artifacts --save-id remove-intents
"""

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
    parser.add_argument('--no-graph', action='store_true', help='disables the graph')
    parser.add_argument('--force', action='store_true', help='completes analysis if save-id already exists')
    parser.add_argument('--fnprms', action='store_true', help="Read output from FNPRMS instead of perfherder")
    return parser.parse_args()


def validate_args(args):
    if bool(args.save_dir) ^ bool(args.save_id):
        raise Exception('if --save-dir is specified, --save-id must be specified too or vice versa')

    if args.force and not bool(args.save_id):
        raise Exception('--force expects --save-id to be specified')


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


def get_fnprms_replicates(input):
    import ast
    values = ast.literal_eval(''.join(input))
    return [e * 1000 for e in values] # convert to ms

def analyze_replicates(replicates, is_fnprms):
    test = 'fnprms-MAIN' if is_fnprms else 'perftest-VIEW'
    return {
        'test': test,
        'replicates': replicates,
        'count': len(replicates),
        'mean': statistics.mean(replicates),
        'median': statistics.median(replicates)
    }


def graph(analysis, save_path, no_graph):
    # Assumes save path is writeable (i.e. dir exists).
    replicates = analysis['replicates']
    #pyplot.plot(range(len(replicates)), replicates)
    #y = [5 for _ in replicates]
    y = range(len(replicates))
    pyplot.scatter(replicates, y)
    if save_path:
        pyplot.savefig(save_path + '-graph.pdf')
    if not no_graph:
        pyplot.show()


def save_analysis(analysis, save_path):
    # Assumes save path is writeable (i.e. dir exists).
    path = save_path + '-analysis.txt'
    with open(path, 'w') as f:
        pprint(analysis, stream=f, compact=True)

    # we can just read in analysis results with ast.literal_eval.
    #json_path = save_path + '-analysis.json'
    #with open(json_path, 'w') as f:
    #    json.dump(analysis, f)


def save_input(input, save_path):
    # Assumes save path is writeable (i.e. dir exists).
    path = save_path + '-input.txt'
    with open(path, 'w') as f:
        print(input, file=f)


def save_json(raw_data, save_path):
    # Assumes save path is writeable (i.e. dir exists).
    path = save_path + '-input.json'
    with open(path, 'w') as f:
        json.dump(raw_data, f)


def main():
    args = parse_args()
    validate_args(args)

    input = [l for l in sys.stdin]
    if not args.fnprms:
        raw_data = get_perfherder_data(input)
        replicates = get_perfherder_replicates(raw_data)
    else:
        replicates = get_fnprms_replicates(input)
    analysis = analyze_replicates(replicates, args.fnprms)


    # tood: helper fun
    save_path = None
    if args.save_dir and args.save_id:
        os.makedirs(args.save_dir, exist_ok=True)
        files = os.listdir(args.save_dir)
        match_files = [f for f in files if f.startswith(args.save_id)]
        if args.force or len(match_files) == 0:
            save_path = os.path.join(args.save_dir, args.save_id)
        else:
            raise Exception('File at {} already exists. Unable to save. Exiting...'.format(args.save_id))

        save_analysis(analysis, save_path)
        save_input('\n'.join(input), save_path) # TODO: janky
        # Input JSON seems unnecessary if we save analysis as json.
        #save_json(raw_data, save_path)
    pprint(analysis, compact=True)
    graph(analysis, save_path, args.no_graph)


if __name__ == '__main__':
    main()
