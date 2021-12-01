#!/usr/bin/env zsh
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

set -e

if [ $# -ne 2 ]; then
    # See here for USAGE:
    echo "expected 2 arguments: <path-to-mozilla-central> <path-to-test-results--relative-to-mc>"
    echo "e.g. ./run-perftest-view ../mozilla-central perftest_results"
    exit 1
fi

pushd $1

./mach perftest \
    --flavor mobile-browser \
    --android \
    --android-app-name org.mozilla.fenix \
    --perfherder-metrics processLaunchToNavStart \
    --android-clear-logcat \
    --android-capture-logcat logcat \
    --android-activity org.mozilla.fenix.IntentReceiverActivity \
    --hooks testing/performance/hooks_android_view.py \
    --perfherder \
    --perfherder-app fenix \
    --browsertime-iterations 25 \
    --output $2 \
    testing/performance/perftest_android_view.js

    # Other options:
    #--browsertime-geckodriver <path> \
    #--browsertime-install-url <url> \

    #--profile-conditioned \
    #--profile-conditioned-scenario settled \
    #--profile-conditioned-platform p2_aarch64-fenix.nightly \
    #--android-perf-tuning \
