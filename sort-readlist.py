#!/usr/bin/python

import logging
import re
import subprocess
import sys
import os

import calibre_config
from calibre.library.database2 import LibraryDatabase2
from calibre.utils.config import prefs

import args

ISSUE_PATTERN = re.compile('(\d+) (.*)$')

args.add_argument('--archive', '-a', help='Archive file before sorting',
                  action='store_true')
args.add_argument('--todobin', '-t', help='path to todo.txt script',
                  type=str, default='todo.sh')
args.add_argument('--infile', '-i', help='path to input file',
                  default=sys.stdin)
args.add_argument('--outfile', '-o', help='path to output file',
                  default=sys.stdout)
args.add_argument('--verbose', '-v', help='Enable verbose logging',
                  action='store_true')

ARGS={}

def get_issues(infile):
  'Find issues listed in "id title" format.'
  for line in infile:
    issueid = ISSUE_PATTERN.match(line)
    if issueid:
      issue_id, issue_name = issueid.groups()
      logging.debug('Found issue "%s"(%d)', issue_id, issue_name)
      yield int(issue_id), issue_name
    else:
      logging.warn('Unable to parse line: %s', line)

def get_issue_details(infile):
  'Look up issue details in Calibre library.'
  db = LibraryDatabase2(prefs['library_path'])
  for issue, title in get_issues(infile):
    mi = db.get_metadata(issue, index_is_id=True)
    if mi:
      logging.debug('Found issue %s(%d)[%s]', title, issue, mi.pubdate)
      # Return tuple with fields in the order to sort by
      yield mi.pubdate, title, issue
    else:
      logging.warn('Unable to find issue in database: %s(%d)', title, issue)

def main():
  logger = logging.getLogger()
  if ARGS.verbose:
    logger.setLevel(logging.DEBUG)

  # archive todo list
  if ARGS.archive:
    try:
      output = subprocess.check_output([ARGS.todobin, 'archive'])
    except CalledProcessError as e:
      logging.error('Unable to archive old items: %s', e.output)

  # Open input and sort by pubdate then name
  infile = ARGS.infile
  if isinstance(infile, basestring):
    infile = open(infile, 'r')
  issues = sorted(get_issue_details(infile))
  if infile is not sys.stdin:
    infile.close()
    
  # Write out sorted list
  outfile = ARGS.outfile
  if isinstance(outfile, basestring):
    outfile = open(outfile, 'w')
  for pubdate, title, idx in issues:
    outfile.write('%d %s\n' % (idx, title))
  if outfile is sys.stdout:
    outfile.flush()
  else:
    outfile.close()

if __name__ == '__main__':
  ARGS = args.parse_args()
  main()
