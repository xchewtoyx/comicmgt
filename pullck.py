#!/usr/bin/python
# Copyright 2013 Russell Heilling
'List titles in pull-list.'

from datetime import date, datetime, timedelta
import logging
import os

import pycomicvine

import api_key
import args
from pulldb import PullList
import logs
from calibredb import CalibreDB

args.add_argument('--pulldb', '-d', help='location of pull database',
                  default=os.path.join(os.environ['HOME'], '.pull.db'))
args.add_argument('--fixissues', action='store_true',
                  help='Fill in comicvineid and volumeid for all issues')
args.add_argument('--fixdates', action='store_true',
                  help='Set volume start dates for all volumes where not set')
args.add_argument('--fixvolnames', action='store_true',
                  help='Set volume names for all volumes where not set.')
ARGS = args.ARGS

def fix_issues(pull_list, calibredb):
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

def fix_start_dates(pull_list):
  for volume in list(pull_list.volumes()):
    volume_start = pull_list.start_date(volume)
    if volume_start and volume_start > date.min:
      continue
    volume_detail = pycomicvine.Volume(volume, field_list=[
        'id', 'name', 'start_year'])
    logging.info('Setting start year for volume: %s (%d) [%s]',
                 volume_detail.name, volume, volume_detail.start_year)
    start_date = date(volume_detail.start_year, 1, 1)
    pull_list.start_date(volume, start_date=start_date)

def fix_volume_names(pull_list):
  for volume in list(pull_list.volumes()):
    name = pull_list.volume_name(volume)
    if name:
      continue
    volume_detail = pycomicvine.Volume(volume, field_list=[
        'id', 'name', 'start_year'])
    logging.info('Setting name for volume: %s (%d) [%s]',
                 volume_detail.name, volume, volume_detail.start_year)
    pull_list.volume_name(volume, volume_detail.name)

def main():
  'Check for new issues to pull.'
  pull_list = PullList(ARGS.pulldb)
  calibredb = CalibreDB()
  if ARGS.fixissues:
    fix_issues(pull_list, calibredb)
  if ARGS.fixdates:
    fix_start_dates(pull_list)
  if ARGS.fixvolnames:
    fix_volume_names(pull_list)

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
