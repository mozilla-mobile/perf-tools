#!/usr/bin/env bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Takes two videos of equal size and combines them, side-by-side with timestamps.
# This can be useful to visually demonstrate the difference between two different
# interactions. For example, you may perform the same behavior in Firefox and
# Chrome, record them, and create a side-by-side.
#
# Be sure to specify the output file with the correct format, e.g. "output.mp4".
#
# To align the videos, you can e.g. open them each in QuickTime, move the cursor
# to the area of the video to clip, go to Edit -> Split Clip, delete the earlier
# part of clip, and save the result.

USAGE="USAGE: ./combine-videos-side-by-side.sh input1 input2 output"

# Ensure we have our args.
: ${1?$USAGE}
: ${2?$USAGE}
: ${3?$USAGE}

INTERMEDIATE_FILE=$3.intermediate.mp4

# Combine videos side-by-side, adapted from https://stackoverflow.com/a/42257415/2219998
ffmpeg -i $1 -i $2 -filter_complex hstack -vsync cfr -r:v 30 $INTERMEDIATE_FILE

# Add timestamps to video, via https://superuser.com/a/1613753
# We couldn't make this a single ffmpeg call with the current args because
# -filter_complex and -vf are mutually exclusive.
ffmpeg -i $INTERMEDIATE_FILE -vf drawtext="fontsize=60:fontcolor=white:text='%{e\:t*1000}':x=(w-text_w):y=(h-text_h)" $3

# Remove intermediate file.
rm -f $INTERMEDIATE_FILE

echo "Saved as $3"
