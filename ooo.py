#!/usr/bin/python

import os
import sys
import re
from collections import defaultdict

COMIC_RE = re.compile(r'^\d+ +([^#]+)#(\d+)')

def lines(todofile):
  with open(todofile) as todolines:
    for line in todolines:
      title_match = COMIC_RE.match(line)
      if title_match:
        # (title, issue)
        yield line.strip(), title_match.group(1), int(title_match.group(2))

def issues(todofile):
  seen = defaultdict(int)
  for line, title, issue in lines(todofile):
    if issue and seen[title] and issue != seen[title]+1:
      yield line, seen[title]
    seen[title] = issue

def main(files):
  for todofile in files:
    for issue, lastissue in issues(todofile):
      print "%s (last seen %d)" % (issue, lastissue)

if __name__ == '__main__':
  main(sys.argv[1:])
