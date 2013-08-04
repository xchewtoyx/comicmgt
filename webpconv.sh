#!/bin/bash
# Copyright 2013 Russell Heilling

TMPDIR=$(mktemp -d)

file=$1
if [ -z "$file" ]; then
  echo Give a filename >/dev/stderr
  exit 1
fi

if [ ! -f "$file" ]; then
  echo File not found $file > /dev/stderr
  exit 1
fi

if [ -f "${file/%cbz/cbr}" ]; then
  echo Output file already exists. Not clobbering. > /dev/stderr
  exit 1
fi

/usr/bin/unzip -q "$file" -d $TMPDIR

for page in $TMPDIR/*.webp; do
  pngfile=$(mktemp --tmpdir="$TMPDIR")
  dwebp "$page" -o "$pngfile" > /dev/null
  /usr/bin/convert "$pngfile" "${page/%webp/jpg}"
done

/usr/bin/rar a -ep -inul "${file/%cbz/cbr}" $TMPDIR/*.{jpg,png}

rm -rf $TMPDIR
