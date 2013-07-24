#!/usr/bin/python

import os
import sys
import re
from collections import defaultdict
import args
ARGS=None
args.add_argument('--noreboots', '-r', action='store_true',
                  help='ignore series reboots')
args.add_argument('--nodups', '-d', action='store_true',
                  help='ignore duplicates')
args.add_argument('--maxdelta', '-m', type=int, default=50,
                  help='Assume larger jumps are intentional')
args.add_argument('files', nargs='*', default=[sys.stdin], 
                  help='Files to merge')


COMIC_RE = re.compile(r'^\d+ +([^#]+)#([^:\s]+)')

def inputfile(todofile):
  if hasattr(todofile, 'readline'):
    return todofile
  else:
    return open(todofile)

def lines(todofile):
  with inputfile(todofile) as todolines:
    for line in todolines:
      title_match = COMIC_RE.match(line)
      if title_match:
        # (title, issue)
        yield line.strip(), title_match.group(1), title_match.group(2)

def issues(todofile):
  seen = defaultdict(int)
  for line, title, issue in lines(todofile):
    if issue and issue.isdigit() and issue != '0':
      if seen[title]:
        delta = abs(float(issue) - float(seen[title]))
        if ((delta == 0 and not ARGS.nodups) or 
            (delta > 1 and delta < ARGS.maxdelta and not (
              int(issue) == 1 and ARGS.noreboots))):
          yield line, seen[title]
      seen[title] = issue

def main():
  for todofile in ARGS.files:
    for issue, lastissue in issues(todofile):
      print "%s (last seen %s)" % (issue, lastissue)

if __name__ == '__main__':
  ARGS = args.parse_args()
  main()
