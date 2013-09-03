#!/usr/bin/python
# Copyright 2013 Russell Heilling
'List titles in pull-list.'

from datetime import date, datetime, timedelta
import logging
import os
import threading

import pycomicvine

import api_key # pylint: disable=W0611
import args
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

def volume_details(volumes):
  'Retrieve volume details from comicvine.'
  volume_filter = '|'.join(str(volume) for volume in volumes)
  return pycomicvine.Volumes(
    filter='id:%s' % (volume_filter,), fields=['id', 'name', 'start_year'])

def issue_details(volumes, sort=None):
  'Retrieve issue details from comicvine.'
  volume_filter = '|'.join(str(volume) for volume in volumes)
  return pycomicvine.Issues(
    filter='volume:%s' % (volume_filter,), fields=[
      'id', 'volume', 'issue_number', 'store_date'],
    sort=sort)

class CheckShard(threading.Thread):
  'Check shard of volumes for missing issues'
  def __init__(self, threadid, thread_count, pull_list):
    super(CheckShard, self).__init__()
    self.threadid = threadid
    self.thread_count = thread_count
    self.pull_list = pull_list
    self.missing_issues = set()
    self.logger = logging.getLogger('shard-%d' % self.threadid)

  def _sharded_to_us(self, volume):
    'Is this volume for us?'
    return volume % self.thread_count == self.threadid

  def run(self):
    'Check for issues found in comicvine but not the seen list.'
    shard_volumes = set()
    for volume in self.pull_list.volumes():
      if self._sharded_to_us(volume):
        shard_volumes.add(volume)
    self.logger.info('Processing %d volumes', len(shard_volumes))
    min_start = min(v for k,v in self.pull_list.volume_starts(
        ).items() if k in shard_volumes)
    volumes = volume_details(shard_volumes)
    issues = set()
    for issue in issue_details(shard_volumes, sort='store_date:desc'):
      if not isinstance(issue, pycomicvine.Issue):
        logging.error('Issue has wrone type: %s, %r', type(issue), issue)
        continue
      if issue.store_date and issue.store_date.date() < min_start:
        break
      issues.add(issue)
    for volume in volumes:
      self.logger.debug('Checking volume %d', volume.id)
      seen_issues = set()
      for issue in self.pull_list.seen_issues(volume.id, cvid=True):
        seen_issues.add(pycomicvine.Issue(issue, do_not_download=True))
      volume_issues = set(issue for issue in issues if issue.volume == volume)
      self.missing_issues.update(volume_issues - seen_issues)
    self.logger.info('Found %d missing issues', len(self.missing_issues))

def check_missing(pull_list):
  'Check for issues found in comicvine but not the seen list.'
  logging.info('Looking for missing issues.')
  missing_issues = set()
  thread_count = 8
  threads = [CheckShard(i, thread_count, pull_list) 
             for i in range(thread_count)]
  for thread in threads:
    thread.start()
  for thread in threads:
    thread.join()
    missing_issues.update(thread.missing_issues)
  if missing_issues:
    logging.info('Found %d missing issues.', len(missing_issues))
  volume_start = pull_list.volume_starts()
  for issue in missing_issues:
    if not isinstance(issue, pycomicvine.Issue):
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
  volumes = set(volume_details(pull_volumes))
  issues = issue_details(pull_volumes, sort='store_date:desc')
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
  for volume in volume_details(pull_list.volumes()):
    print '%d - %s (%d)' % (volume.id, volume.name, volume.start_year)

def add_volumes(pull_list):
  'Add new volumes to the pull list.'
  volumes = set()
  for add_vol in ARGS.add:
    volumes.update(add_vol.split(','))
  logging.info('Found %d volumes to add.', len(volumes))
  for volume in volumes:
    pull_list.add_volume(int(volume))

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
