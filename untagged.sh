#!/bin/sh

calibredb list -s identifiers:comicvine:false -f title -w 800 | \
    grep -v -e ^id -e ^$ | \
    sed 's/_/ /g;                      # Replace _ with space
        s/ \+/ /g;                     # Strip any double spaces
        s/([^)]*[^0-9)][^)]*)//g;      # Strip all non-year bracketed exprn
        s/\([^ ]\)(/\1 (/g;            # Add a space before any (
        s/2000AD/2000 AD/;             # Fixup common mis-naming
        s/# 0/#/;                      # Fix space between # and number
        s/ \+$//;                      # Remove trailing space
        s/^\([0-9]\+\) \(.*\)/fem.sh \1 t:"\2"/'
