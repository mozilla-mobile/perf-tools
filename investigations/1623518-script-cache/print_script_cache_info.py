#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Usage:
- `touch config.yaml` and add contents:
```
env:
    MOZ_LOG: JSComponentLoader:5
```
- `adb push config.yaml /data/local/tmp/org.mozilla.fenix-geckoview-config.yaml`
- `adb shell am set-debug-app --persistent org.mozilla.fenix`
- `adb logcat -c`
- Launch app
- `adb logcat -d | print_script_cache_info.py`

And you probably want to stop the app and run it again to see what script have come from the cache.
"""

import sys
from pprint import pprint

PREFIX_SLOW = 'Slow loading '  # Slow loading resource://gre/modules/osfile/osfile_shared_allthreads.jsm
PREFIX_CACHE = 'Successfully loaded '  # Successfully loaded resource://gre/modules/GeckoViewAutofill.jsm from cache

TAG = 'JSComponentLoader '

parent_cache = []
child_cache = []
parent_slow = []
child_slow = []

for line in sys.stdin:
    index = line.find(TAG)
    if index < 0:
        continue

    if '[Child ' in line:
        cache = child_cache
        slow = child_slow
    elif '[Parent ' in line:
        cache = parent_cache
        slow = parent_slow
    else:
        raise Exception('unexpected line ' + line)

    subline = line[index + len(TAG):].strip()
    if subline.startswith(PREFIX_SLOW):
        slow.append(subline[len(PREFIX_SLOW):])
    elif subline.startswith(PREFIX_CACHE):
        cache_line = subline[len(PREFIX_CACHE):]
        cache.append(cache_line[:cache_line.find(' ')])


def print_attr(name, process, obj):
    print('--- {}: {} {} ---'.format(process, name, len(obj)))
    pprint(obj)
    print('\n')


print_attr('CACHED', 'PARENT', parent_cache)
print_attr('SLOW', 'PARENT', parent_slow)
print_attr('CACHED', 'CHILD', child_cache)
print_attr('SLOW', 'CHILD', child_slow)
