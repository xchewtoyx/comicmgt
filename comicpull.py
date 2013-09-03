#!/usr/bin/python
# Copyright 2013 Russell Heilling
# pylint: disable=C0103
'''Comic pull-list management.

Manage titles on pull-list and add new titles to toread list.
'''
import logging
import os

import args
from calibredb import CalibreDB
import logs
from pulldb import PullList
from toread import ReadingList

ARGS = args.ARGS

args.add_argument('--add_volume', '-a', action='append',
                  help='comicvine volume to add to pull-list.')
args.add_argument('--nopull', '-n', action='store_true',
                  help='Don\'t check for new issues')
args.add_argument('--todo_file', help='Location of todo.txt file',
                  default=os.path.join(os.environ['HOME'],
                                       'Dropbox/todo/todo.txt'))
args.add_argument('--pulldb', '-p', help='Location of pull database',
                  default=os.path.join(os.environ['HOME'], '.pull.db'))

def pull_issues(pull_list):
  'Check for unseen issues in database and add them to toread list.'
  calibredb = CalibreDB()
  # Check database for new issues for pull volumes
  new_issues = []
  for volume in pull_list.volumes():
    logging.info('Checking volume %d for new issues', volume)
    seen_issues = pull_list.seen_issues(volume)
    calibredb.search(query='identifiers:comicvine-volume:%d' % volume)
    for issue in calibredb.data:
      issueid = issue[calibredb.FIELD_MAP['id']]
      identifiers = {}
      for ident in issue[calibredb.FIELD_MAP['identifiers']].split(','):
        identifiers.update((ident.split(':'),))
      cvid = identifiers.get('comicvine')
      
      if issueid in seen_issues:
        logging.debug('Issue %d already seen in volume %d', issueid, volume)
        continue
      # Sometimes issues will be retagged after being pulled.  Double
      # check that the issue isn't in the database associated with a
      # different volume before pulling.
      if pull_list.seen_issue(issue['id']):
        logging.warn('Issue %d seen but not associated with volume %d',
                      issueid, volume)
        continue
      logging.info('Found unseen issue %d', issueid)
      new_issues.append((issueid, issue['title'], volume, cvid))
  # Update toread list
  if new_issues:
    toread = ReadingList(ARGS.todo_file)
    toread.add_issues(new_issues)
    for (issue, _, volume, cvid) in new_issues:
      pull_list.add_issue(int(issue), volume, cvid)

def main():
  'Check for new issues to pull.'
  pull_list = PullList(ARGS.pulldb)
  # Add new volumes
  if ARGS.add_volume:
    for volume in [int(vol) for vol in ARGS.add_volume]:
      if not pull_list.pull_volume(volume):
        pull_list.add_volume(int(volume))
  if not ARGS.nopull:
    pull_issues(pull_list)

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
