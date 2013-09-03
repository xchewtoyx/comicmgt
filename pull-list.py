#!/usr/bin/python
# Copyright 2013 Russell Heilling
'List titles in pull-list.'

from datetime import date, datetime, timedelta
import logging
import os
import threading

import api_key # pylint: disable=W0611
import args
import cvdb
from pulldb import PullList
import logs


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

def check_missing(pull_list):
  'Check for issues found in comicvine but not the seen list.'
  logging.info('Looking for missing issues.')
  missing_issues = set()
  thread_count = 8
  threads = [cvdb.CheckShard(i, thread_count, pull_list) 
             for i in range(thread_count)]
  for thread in threads:
    thread.start()
  for thread in threads:
    thread.join()
    missing_issues.update(thread.missing_issues)
  if missing_issues:
    logging.info('Found %d missing issues.', len(missing_issues))
  volume_start = pull_list.volume_starts()
  for issue in sorted(missing_issues, key=lambda i: i.store_date.date()):
    if not isinstance(issue, cvdb.Issue):
      logging.warn('Issue has wrong type: %s %r', type(issue), issue)
      continue
    if issue.store_date:
      issue_date = issue.store_date.date()
    else:
      issue_date = date.min
    if issue_date > volume_start[issue.volume.id]:
      print 'Missing: %s #%s (%d/%d) [%s]' % (
        issue.volume.name, issue.issue_number, issue.volume.id, 
        issue.id, issue.store_date)

def check_expired(pull_list):
  'Check for pulled volumes that have not had a new issue in a while.'
  logging.info('Checking for volumes with no issues within last %d days',
               ARGS.expire_limit)
  today = datetime.now()
  pull_volumes = list(pull_list.volumes())
  fresh_volumes = set()
  volumes = set(cvdb.volume_details(pull_volumes))
  issues = cvdb.issue_details(pull_volumes, sort='store_date:desc')
  expire_limit = timedelta(int(ARGS.expire_limit))
  for issue in issues:
    if issue.store_date and today - issue.store_date > expire_limit:
      break
    fresh_volumes.add(issue.volume)
  expired_volumes = volumes - fresh_volumes
  for volume in expired_volumes:
    logging.warn('Volume %s (%d) has no issues in last %d days.',
                 volume.name, volume.id, int(ARGS.expire_limit))

def do_list(pull_list):
  'List the titles currently on the pull list.'
  logging.info('Retrieving metadata for pulled volumes.')
  for volume in cvdb.volume_details(pull_list.volumes()):
    print '%d - %s (%d)' % (volume.id, volume.name, volume.start_year)

def add_volumes(pull_list):
  'Add new volumes to the pull list.'
  volumes = set()
  for add_vol in ARGS.add:
    volumes.update(add_vol.split(','))
  logging.info('Found %d volumes to add.', len(volumes))
  for volume in map(int, volumes):
    volume_data = cvdb.Volume(volume, field_list=[
        'id','name','start_year'])
    pull_list.add_volume(volume, metadata=volume_data)

def remove_volumes(pull_list):
  'Remove volumes from the pull list.'
  volumes = set()
  for rm_vol in ARGS.remove:
    volumes.update(rm_vol.split(','))
  logging.info('Found %d volumes to remove.', len(volumes))
  for volume in volumes:
    pull_list.remove_volume(int(volume))

def main():
  'Check for new issues to pull.'
  pull_list = PullList(ARGS.pulldb)
  if ARGS.add:
    add_volumes(pull_list)
  if ARGS.remove:
    remove_volumes(pull_list)
  if ARGS.expire:
    check_expired(pull_list)
  if ARGS.check:
    check_missing(pull_list)
  if ARGS.list:
    do_list(pull_list)

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
