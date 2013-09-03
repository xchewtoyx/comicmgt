# Copyright 2013 Russell Heilling
'Functions and classes for accessing comicvine data'

from datetime import date, datetime, timedelta
import logging
import os
import random
import time
import threading

import pycomicvine
from pycomicvine import Issue, Issues, Volumes
from pycomicvine.error import InvalidResourceError

import api_key # pylint: disable=W0611

def volume_details(volumes):
  'Retrieve volume details from comicvine.'
  volume_filter = '|'.join(str(volume) for volume in volumes)
  return pycomicvine.Volumes(
    filter='id:%s' % (volume_filter,), field_list=['id', 'name', 'start_year'])

def issue_details(volumes, sort=None):
  'Retrieve issue details from comicvine.'
  volume_filter = '|'.join(str(volume) for volume in volumes)
  return pycomicvine.Issues(
    filter='volume:%s' % (volume_filter,), field_list=[
      'id', 'volume', 'issue_number', 'store_date'],
    sort=sort)

class CheckShard(threading.Thread):
  'Check shard of volumes for missing issues'
  def __init__(self, threadid, thread_count, pull_list, retries=2):
    super(CheckShard, self).__init__()
    self.threadid = threadid
    self.thread_count = thread_count
    self.pull_list = pull_list
    self.missing_issues = set()
    self.logger = logging.getLogger('shard-%d' % self.threadid)
    self.retries = retries

  def _sharded_to_us(self, volume):
    'Is this volume for us?'
    return volume % self.thread_count == self.threadid

  def lookup_issues(self, min_start, issues):
    'Attempt to lookup issues of interest using the comicvine api.'
    for issue in issue_details(self.shard_volumes, sort='store_date:desc'):
      # If we retry, keep issues from the previous run
      if issue in issues:
        continue
      if not isinstance(issue, pycomicvine.Issue):
        logging.error('Issue has wrong type: %s, %r', type(issue), issue)
        continue
      if issue.store_date and issue.store_date.date() < min_start:
        break
      issues.add(issue)
    for volume in volume_details(self.shard_volumes):
      self.logger.debug('Checking volume %d', volume.id)
      seen_issues = set()
      for issue in self.pull_list.seen_issues(volume.id, cvid=True):
        seen_issues.add(pycomicvine.Issue(issue, do_not_download=True))
      volume_issues = set(issue for issue in issues if issue.volume == volume)
      self.missing_issues.update(volume_issues - seen_issues)
      # Once we have completed a volume remove it from the list so we
      # don't have to reprocess it in case of retry.
      self.shard_volumes.remove(volume.id)
  
  def run(self):
    'Check for issues found in comicvine but not the seen list.'
    self.shard_volumes = set()
    for volume in self.pull_list.volumes():
      if self._sharded_to_us(volume):
        self.shard_volumes.add(volume)
    self.logger.info('Processing %d volumes', len(self.shard_volumes))
    min_start = min(v for k,v in self.pull_list.volume_starts(
        ).items() if k in self.shard_volumes)
    issues = set()
    for retry in range(1, self.retries+1):
      # Sometimes the comicvine API will throw an exception for a good query.
      # To account this retry the query self.retries times to see if the  
      # error is transient.
      try:
        self.logger.info('Run %d/%d: %d volumes remaining', retry, 
                         self.retries, len(self.shard_volumes))
        self.lookup_issues(min_start, issues)
      # TODO(rgh): Remove NameError after bug in pycomicvine resolved.
      except (KeyError, NameError, ValueError, InvalidResourceError) as err:
        self.logger.error(
          "Error retrieving issue details: %r [attempt %d/%d]", 
          err, retry, self.retries)
        if retry == self.retries:
          raise
        # API errors may indicate busy servers.  Back off for
        # 100-600ms before retrying
        time.sleep(random.random()/2 + 0.1)
      else:
        break
    self.logger.info('Found %d missing issues', len(self.missing_issues))
