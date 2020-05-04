#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import fileinput
import sys
from statistics import mean # 👿 !

# This script will read logcat text from stdin, parse out duration values in the format
# specified below, and sum them. This is valuable to avoid having to do so by hand, an
# error prone operation.
#
# This script will parse out duration values values in the following format:
#     2020-05-04 15:15:50.340 10845-10845/? E/lol: average 37
# In particular, the logcat message must be 'average <duration>'; the reminder of the
# log or log tag does not matter. All other lines will be ignored.
#
# Example usage:
# $ cat logcat-output.txt | ./average-logcat.py
#
# Sample output:
# 10 runs, average: 36.7
# [41, 40, 38, 37, 40, 37, 37, 37, 30, 30]

MATCH_STR = 'average '
EXPECTED_FORMAT = '2020-05-04 15:15:50.340 10845-10845/? E/lol: average 37'

if __name__ == "__main__":
    values = []
    for line in fileinput.input():
        # The message will be after the last colon because we demand a certain formatting.
        message_text = line[line.rfind(': ') + 2:]  # +2 to move past ': '.

        if message_text and message_text.startswith(MATCH_STR):
            values.append(int(message_text[len(MATCH_STR):]))

    if len(values) == 0:
        print('WARN: no lines matched. expected format like:\n    {}'.format(EXPECTED_FORMAT))
    else:
        log_output = "{} runs, average: {}".format(len(values), mean(values))
        print(log_output)
        print(values)
