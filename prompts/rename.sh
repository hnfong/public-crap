#!/bin/bash
#
# Rename all files of prefix1 to prefix2
prefix1=$1
shift
prefix2=$1
shift

for file in "$prefix1"*; do
    mv -v "$file" "$prefix2${file#$prefix1}"
done
