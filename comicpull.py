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

args.add_argument('--todo_file', help='Location of todo.txt file',
                  default=os.path.join(os.environ['HOME'],
                                       'Dropbox/todo/todo.txt'))
args.add_argument('--pulldb', '-p', help='Location of pull database',
                  default=os.path.join(os.environ['HOME'], '.pull.db'))
args.add_argument('--volume', help='Volume to pull',
                  action='append')
args.add_argument('--workers', help='Number of worker threads.',
                  default=1, type=int)
args.add_argument('--shard', help='The task number to run',
                  default=0, type=int)

def check_new(volume, pull_list=None, calibredb=None):
  logging.debug('Checking volume %d for new issues', volume)
  seen_issues = pull_list.seen_issues(volume)
  new_issues = set()
  logging.debug('Checking for issues in Calibre Database for volume %d',
                volume)
  issues = calibredb.search(
    query='identifiers:comicvine-volume:%d' % volume, return_matches=True)
  for issueid in issues:
    if issueid in seen_issues:
      logging.debug('Issue %d already seen in volume %d', 
                    issueid, volume)
      continue
    # Sometimes issues will be retagged after being pulled.  Double
    # check that the issue isn't in the database associated with a
    # different volume before pulling.
    if pull_list.seen_issue(issueid):
      logging.warn('Issue %d seen but not associated with volume %d',
                   issueid, volume)
      continue

    logging.info('Found unseen issue %d', issueid)
    issue = calibredb.issue(issueid)
    cvid = issue.identifiers.get('comicvine')
    new_issues.add((issueid, issue.title, volume, cvid))
  return new_issues

def sharded_to_us(volume):
  return volume % ARGS.workers == ARGS.shard

def pull_issues(pull_list):
  'Check for unseen issues in database and add them to toread list.'
  calibredb = CalibreDB()
  # Check database for new issues for pull volumes
  new_issues = set()
  if ARGS.volume:
    volumes = map(int, ARGS.volume)
  else:
    volumes = pull_list.volumes()
  for volume in volumes:
    if sharded_to_us(volume):
      new_issues.update(
        check_new(volume, pull_list=pull_list, calibredb=calibredb))
  # Update toread list
  if new_issues:
    toread = ReadingList(ARGS.todo_file)
    toread.add_issues(new_issues)
    for (issue, _, volume, cvid) in new_issues:
      pull_list.add_issue(int(issue), volume, cvid)

def main():
  'Check for new issues to pull.'
  pull_list = PullList(ARGS.pulldb)
  pull_issues(pull_list)

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
