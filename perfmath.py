#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import datetime
import statistics


def percent_change(old, new):
    # Ensure we're not using truncating integers.
    old = float(old)
    new = float(new)

    # formula via https://www.mathsisfun.com/numbers/percentage-change.html
    return (new - old) / abs(old) * 100


def percent_difference(v1, v2):
    # Ensure we're not using truncating integers.
    v1 = float(v1)
    v2 = float(v2)

    # formula via https://www.mathsisfun.com/percentage-difference.html
    numerator = abs(v1 - v2)
    denominator = statistics.mean([v1, v2])
    return abs(numerator / denominator) * 100


def screenrecord_timestamp_diff(start_str, end_str):
    """Measures the difference between two timestamps taken from
    `adb shell screenrecord --bugreport`. Sample timestamp: 14:42:18.291
    """
    def to_datetime(s):
        return datetime.strptime(s + '000', '%H:%M:%S.%f')  # + '000' so to micros
    diff = to_datetime(end_str) - to_datetime(start_str)
    return diff.total_seconds() * 1000  # returning millis.


def main():
    print("""main() usage is unsupported. Please import perfmath from within a python interpreter. For example:

$ python3
>>> import perfmath
>>> perfmath.percent_change(10, 4)
-60.0
>>> perfmath.percent_difference(10, 4)
85.71428571428571
""")


if __name__ == '__main__':
    main()
