#!/usr/bin/python
# Copyright 2013 Russell Heilling
# pylint: disable=C0103
'''Comic pull-list management.

Manage titles on pull-list and add new titles to toread list.
'''
import logging
import os
import sqlite3
import sys

import args
from calibredb import CalibreDB, set_log_level

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
args.add_argument('--verbose', '-v', action='count',
                  help='Enable verbose logging.')

class PullList(object):
  def __init__(self, pulldb):
    self.pulldb = pulldb
    self._check_tables()

  def _check_tables(self):
    with sqlite3.connect(self.pulldb) as conn:
      tables = [table for (table,) in conn.execute(
        "SELECT tbl_name FROM SQLITE_MASTER WHERE type = 'table'")]
      if 'pull_volumes' not in tables:
        self._create_pull_volumes()
      if 'seen_issues' not in tables:
        self._create_seen_issues()

  def _create_pull_volumes(self):
    logging.info('Creating pull_volumes table')
    with sqlite3.connect(self.pulldb) as conn:
      conn.execute("CREATE TABLE pull_volumes (volume INTEGER PRIMARY KEY)")

  def _create_seen_issues(self):
    logging.info('Creating seen_issues table')
    with sqlite3.connect(self.pulldb) as conn:
      conn.execute("CREATE TABLE seen_issues (issue INTEGER PRIMARY KEY)")

  def add_issue(self, issueid):
    logging.debug('Adding %d to issue list.', issueid)
    with sqlite3.connect(self.pulldb) as conn:
      try:
        conn.execute('INSERT INTO seen_issues (issue) VALUES (?)', (issueid,))
      except sqlite3.IntegrityError:
        logging.warn('Issue %d is already added', issueid)

  def add_volume(self, volumeid):
    logging.debug('Adding %d to volume list.', volumeid)
    with sqlite3.connect(self.pulldb) as conn:
      try:
        conn.execute(
          'INSERT INTO pull_volumes (volume) VALUES (?)', (volumeid,))
      except sqlite3.IntegrityError:
        logging.warn('Volume %d is already added', volumeid)

  def pull_volume(self, volumeid):
    logging.debug('Looking up volume id %d', volumeid)
    pull = False
    with sqlite3.connect(self.pulldb) as conn:
      c = conn.execute('SELECT volume FROM pull_volumes WHERE volume=?', 
                       (volumeid,))
      (result,) = c.fetchone()
      if result == volumeid:
        pull = True
    return pull

  def seen_issue(self, issueid):
    logging.debug('Looking up issue id %d', issueid)
    seen = False
    with sqlite3.connect(self.pulldb) as conn:
      c = conn.execute('SELECT issue FROM seen_issues WHERE issue=?', 
                       (issueid,))
      (result,) = c.fetchone()
      if result == issueid:
        seen = True
    return seen

  def volumes(self):
    with sqlite3.connect(self.pulldb) as conn:
      for (volume,) in conn.execute('SELECT volume FROM pull_volumes'):
        yield volume

class ReadingList(object):
  def __init__(self, readinglist):
    self.readinglist = readinglist

  def add_issues(self, issues):
    with open(self.readinglist, 'a') as reading_file:
      for issue in issues:
        reading_file.write('%d %s\n' % issue)

def set_logging():
  logger = logging.getLogger()
  level = logging.WARN
  if ARGS.verbose > 1:
    level = logging.DEBUG
  if ARGS.verbose == 1:
    level = logging.INFO
  logger.setLevel(level)
  set_log_level(level)

def main():
  calibredb = CalibreDB()
  pull_list = PullList(ARGS.pulldb)
  # Add new volumes
  if ARGS.add_volume:
    for volume in [int(vol) for vol in ARGS.add_volume]:
      if not pull_list.pull_volume(volume):
        pull_list.add_volume(int(volume))
  if not ARGS.nopull:
    # Check database for new issues for pull volumes
    new_issues = []
    for volume in pull_list.volumes():
      logging.info('Found volume %d', volume)
      calibredb.search(query='identifiers:comicvine-volume:%d' % volume)
      for issue in calibredb.get_data_as_dict():
        if not pull_list.seen_issue(issue['id']):
          logging.debug('Found unseen issue %d', issue['id'])
          new_issues.append((issue['id'], issue['title']))
    # Update toread list
    if new_issues:
      toread = ReadingList(ARGS.todo_file)
      toread.add_issues(new_issues)
      for (issue, title) in new_issues:
        pull_list.add_issue(int(issue))

if __name__ == '__main__':
  args.parse_args()
  set_logging()
  try:
    main()
  except KeyboardInterrupt:
    sys.exit(1)
