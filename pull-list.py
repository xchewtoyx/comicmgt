#!/usr/bin/python
# Copyright 2013 Russell Heilling
'List titles in pull-list.'

import os

import pycomicvine

import api_key # pylint: disable=W0611
import args
from pulldb import PullList
import logs


args.add_argument('--pulldb', '-d', help='location of pull database',
                  default=os.path.join(os.environ['HOME'], '.pull.db'))
ARGS = args.ARGS

def main():
  'Check for new issues to pull.'
  pull_list = PullList(ARGS.pulldb)
  volume_filter = '|'.join(str(volume) for volume in pull_list.volumes())
  for volume in pycomicvine.Volumes(
    filter='id:%s' % (volume_filter,), fields=['id', 'name', 'start_year']):
    print '%d - %s (%d)' % (volume.id, volume.name, volume.start_year)

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
