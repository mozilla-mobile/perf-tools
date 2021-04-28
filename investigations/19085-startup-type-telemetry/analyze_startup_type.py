# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Takes raw SQL CSV data of the format:

count | startup_type | client_id
<int> | <str>  | <uuid>

where the count is summed, grouped by startup_type and client_id.

And returns the median startup_type counts, i.e.: {
    startup_type: <median>, ...
}

We do this in python locally because I was struggling to do it in SQL.
To get the data, you can download it from redash directly.
See this query: https://sql.telemetry.mozilla.org/queries/79700/source

You may need to uncomment the part for "For direct data downloads"
"""

import csv
import statistics
from collections import defaultdict
from matplotlib import pyplot as plt
from pprint import pprint

def get_data():
    with open('perf_startup_startup_type_normalized.csv') as f:
        return list(csv.reader(f))


def normalize(data):
    '''The raw data omits 0s if a client has not submitted a certain type of startup.
    Therefore, if we don't normalize, we don't take these clients into account when
    calculating the median.
    '''
    all_startup_labels = set([label for _, label, _ in data])
    def all_startup_labels_to_zero():
        return {label: 0 for label in all_startup_labels}

    client_id_to_startup_type_count = defaultdict(all_startup_labels_to_zero)
    for count, startup_type, client_id in data:
        client_id_to_startup_type_count[client_id][startup_type] += int(count)

    # unroll back to input format (rows).
    normalized_data = []
    for client_id, startup_type_to_count in client_id_to_startup_type_count.items():
        for startup_type, count in startup_type_to_count.items():
            normalized_data.append([str(count), startup_type, client_id])

    return normalized_data


def get_medians_unnormalized(data):
    labels_to_replicates = defaultdict(list)
    for count, startup_type, client_id in data:
        labels_to_replicates[startup_type].append(int(count))

    return {label: statistics.median(replicates) for label, replicates in labels_to_replicates.items()}


def plot(medians):
    # Multiple zero values will overlap each other and be illegible so we filter them out.
    filtered = {key: value for key, value in medians.items() if value > 0}

    # Sorting makes it a little easier to find the largest values.
    sorted_medians = dict(sorted(filtered.items(), key=lambda i: i[1]))

    labels = ['{}: {}'.format(startup_type, count) for startup_type, count in sorted_medians.items()]
    plt.pie(sorted_medians.values(), labels=labels, autopct='{:.1f}%'.format)
    plt.show()


def get_data_and_print_for_report(should_plot=True):
    data = get_data()
    data.pop(0)  # remove header

    print('Unnormalized medians:')
    unnormalized_medians = get_medians_unnormalized(data)
    pprint(unnormalized_medians)
    if should_plot: plot(unnormalized_medians)

    print('\nNormalized medians:')
    normalized_data = normalize(data)
    medians = get_medians_unnormalized(normalized_data)
    pprint(medians)
    if should_plot: plot(medians)


def main():
    get_data_and_print_for_report()


if __name__ == '__main__':
    main()
