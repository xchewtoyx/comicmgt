#!/usr/bin/python
# Copyright 2013 Russell Heilling
'''Comic pull-list management.

Manage titles on pull-list and add new titles to toread list.
'''
import logging
import sqlite3

import args

ARGS = args.ARGS

class PullList(object):
  '''Comics pull-list object.

  An interface to a sqlite database containing the volumes to pull and
  the issues already pulled.
  '''
  def __init__(self, pulldb):
    self.pulldb = pulldb
    self._check_tables()

  def _check_tables(self):
    'Check the tables required exist and if not create them.'
    with sqlite3.connect(self.pulldb) as conn:
      tables = [table for (table,) in conn.execute(
        "SELECT tbl_name FROM SQLITE_MASTER WHERE type = 'table'")]
      if 'pull_volumes' not in tables:
        self._create_pull_volumes()
      if 'seen_issues' not in tables:
        self._create_seen_issues()

  def _create_pull_volumes(self):
    'Create the pull_volumes table.'
    logging.info('Creating pull_volumes table')
    with sqlite3.connect(self.pulldb) as conn:
      conn.execute("CREATE TABLE pull_volumes (volume INTEGER PRIMARY KEY)")

  def _create_seen_issues(self):
    'Create the seen_issues table.'
    logging.info('Creating seen_issues table')
    with sqlite3.connect(self.pulldb) as conn:
      conn.execute(
        "CREATE TABLE seen_issues (issue INTEGER PRIMARY KEY, volume INTEGER)")

  def add_issue(self, issueid, volumeid=None):
    'Add an issue to the seen_issues table.'
    logging.debug('Adding %d to issue list.', issueid)
    with sqlite3.connect(self.pulldb) as conn:
      try:
        conn.execute('INSERT INTO seen_issues (issue, volume) VALUES (?,?)', 
                     (issueid,volumeid))
      except sqlite3.IntegrityError:
        logging.warn('Issue %d is already added', issueid)

  def add_volume(self, volumeid):
    'Add a volume to the pull list.'
    logging.debug('Adding %d to volume list.', volumeid)
    with sqlite3.connect(self.pulldb) as conn:
      try:
        conn.execute(
          'INSERT INTO pull_volumes (volume) VALUES (?)', (volumeid,))
      except sqlite3.IntegrityError:
        logging.warn('Volume %d is already added', volumeid)

  def pull_volume(self, volumeid):
    'Check whether a volume is in the pull-list.'
    logging.debug('Looking up volume id %d', volumeid)
    pull = False
    with sqlite3.connect(self.pulldb) as conn:
      cursor = conn.execute('SELECT volume FROM pull_volumes WHERE volume=?', 
                       (volumeid,))
      result = cursor.fetchone()
      if result and result[0] == volumeid:
        pull = True
    return pull

  def seen_issue(self, issueid):
    'Check whether an issue has been seen before.'
    logging.debug('Looking up issue id %d', issueid)
    seen = False
    with sqlite3.connect(self.pulldb) as conn:
      cursor = conn.execute('SELECT issue FROM seen_issues WHERE issue=?', 
                       (issueid,))
      result = cursor.fetchone()
      if result and result[0] == issueid:
        seen = True
    return seen

  def seen_issues(self, volumeid):
    'Return list of issues that have been seen for a particular volume.'
    logging.debug('Looking up seen issues for volume %d', volumeid)
    issues = []
    with sqlite3.connect(self.pulldb) as conn:
      cursor = conn.execute('SELECT issue FROM seen_issues WHERE volume=?',
                            (volumeid,))
      results = cursor.fetchall()
      if results:
        issues = [result[0] for result in results]
    return issues

  def volumes(self):
    'Pulled volumes list generator.'
    with sqlite3.connect(self.pulldb) as conn:
      for (volume,) in conn.execute('SELECT volume FROM pull_volumes'):
        yield volume
