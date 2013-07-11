#!/usr/bin/python

import os
import sys
import re
from collections import defaultdict

COMIC_RE = re.compile(r'^\d+ +([^#]+)#([\d.]+)')

def lines(todofile):
  with open(todofile) as todolines:
    for line in todolines:
      title_match = COMIC_RE.match(line)
      if title_match:
        # (title, issue)
        yield line.strip(), title_match.group(1), title_match.group(2)

def issues(todofile):
  seen = defaultdict(int)
  for line, title, issue in lines(todofile):
    if issue and issue != '0':
      if seen[title]:
        delta = abs(float(issue) - float(seen[title]))
        if delta == 0 or delta > 1:
          yield line, seen[title]
      seen[title] = issue

def main(files):
  for todofile in files:
    for issue, lastissue in issues(todofile):
      print "%s (last seen %s)" % (issue, lastissue)

if __name__ == '__main__':
  main(sys.argv[1:])
