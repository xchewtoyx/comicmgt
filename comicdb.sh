#!/bin/bash
# Copyright 2013 Russell Heilling

calibredb list -f title "$@" -w 800 | sed 's/ \+$//; s/:[^#]\+$//'
