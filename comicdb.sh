#!/bin/bash
# Copyright 2013 Russell Heilling

calibredb "$@" -w 800 | sed 's/ \+$//; s/:[^#]\+$//'
