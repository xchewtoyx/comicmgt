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

TODO_DIR = os.path.join(os.environ['HOME'], 'Dropbox', 'todo')
ISSUE_PATTERN = re.compile('(\d+) (.*)$')

args.add_argument('--todobin', '-t', help='path to todo.txt script',
                  type=str, default='todo.sh')
args.add_argument('--todofile', '-f', help='path to todo.txt file',
                  type=str, default=os.path.join(TODO_DIR, 'todo.txt'))
args.add_argument('--verbose', '-v', help='Enable verbose logging',
                  action='store_true')

ARGS={}

def get_issues():
  for line in open(ARGS.todofile, 'r'):
    issueid = ISSUE_PATTERN.match(line)
    if issueid:
      yield int(issueid.group(1)), issueid.group(2)

def get_issue_details():
  db = LibraryDatabase2(prefs['library_path'])
  for issue, title in get_issues():
    mi = db.get_metadata(issue, index_is_id=True)
    yield mi.pubdate, title, issue

def main():
  logger = logging.getLogger()
  if ARGS.verbose:
    logger.setLevel(logging.DEBUG)
  # archive todo list
  try:
    output = subprocess.check_output([ARGS.todobin, 'archive'])
  except CalledProcessError as e:
    logging.error('Unable to archive old items: %s', e.output)
  issues = sorted(get_issue_details())
    
  # Write out sorted list
  for pubdate, title, idx in issues:
    print "%d %s" % (idx, title)

if __name__ == '__main__':
  ARGS = args.parse_args()
  main()

