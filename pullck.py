#!/usr/bin/python
# Copyright 2013 Russell Heilling
'List titles in pull-list.'

from datetime import datetime, timedelta
import logging
import os

import args
from pulldb import PullList
import logs
from calibredb import CalibreDB

args.add_argument('--pulldb', '-d', help='location of pull database',
                  default=os.path.join(os.environ['HOME'], '.pull.db'))
args.add_argument('--list', '-l', help='List volumes on pull-list.',
                  default=True, action='store_true')
args.add_argument('--nolist', help='Do not list volumes on pull-list.',
                  dest='list', action='store_false')
args.add_argument('--expire', '-x', action='store_true',
                  help='Check for volumes with no issues for defined period.')
args.add_argument('--expire_limit', '-e', help='Expiry period in days',
                  default=90, type=int)
args.add_argument('--check', '-c', help='Check for missing issues', 
                  action='store_true')
args.add_argument('--add', '-a', help='Add a volume to the pull list',
                  action='append')
args.add_argument('--remove', '-r', help='Remove a volume from the pull list',
                  action='append')
ARGS = args.ARGS

def main():
  'Check for new issues to pull.'
  pull_list = PullList(ARGS.pulldb)
  calibredb = CalibreDB()
  for volume in list(pull_list.volumes()):
    for issue in list(pull_list.seen_issues(volume)):
      issue = int(issue)
      metadata = calibredb.issue(issue)
      pull_list.add_issue(issue, volumeid=volume,
                          cvid=int(metadata.identifiers.get('comicvine')))
  for issue in pull_list.seen_issues(None):
    issue = int(issue)
    metadata = calibredb.issue(issue)
    pull_list.add_issue(
      issue, volumeid=int(metadata.identifiers.get('comicvine-volume')),
      cvid=int(metadata.identifiers.get('comicvine')))

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
