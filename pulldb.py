#!/usr/bin/python
# Copyright 2013 Russell Heilling
'''Comic pull-list management.

Manage titles on pull-list and add new titles to toread list.
'''
from datetime import date, datetime
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
      conn.execute("CREATE TABLE pull_volumes (volume INTEGER PRIMARY KEY, "
                   "start_date TIMESTAMP, name TEXT)")

  def _create_seen_issues(self):
    'Create the seen_issues table.'
    logging.info('Creating seen_issues table')
    with sqlite3.connect(self.pulldb) as conn:
      conn.execute(
        "CREATE TABLE seen_issues (issue INTEGER PRIMARY KEY, cvid INTEGER, "
        "volume INTEGER)")

  def add_issue(self, issueid, volumeid=None, cvid=None):
    'Add an issue to the seen_issues table.'
    logging.debug('Adding %d to issue list.', issueid)
    with sqlite3.connect(self.pulldb) as conn:
      try:
        conn.execute(
          'INSERT OR REPLACE INTO seen_issues (issue, volume, cvid) '
          'VALUES (?,?,?)', (issueid,volumeid,cvid))
      except sqlite3.IntegrityError:
        logging.warn('Issue %d is already added', issueid)

  def add_volume(self, volumeid, metadata=None):
    'Add a volume to the pull list.'
    logging.debug('Adding %d to volume list.', volumeid)
    with sqlite3.connect(self.pulldb) as conn:
      try:
        conn.execute(
          'INSERT INTO pull_volumes (volume) VALUES (?)', (volumeid,))
      except sqlite3.IntegrityError:
        logging.warn('Volume %d is already added', volumeid)
      if metadata:
        start_date = date(metadata.start_year, 1, 1)
        conn.execute(
          'UPDATE pull_volumes set name=?,start_date=? WHERE volume=?',
          (metadata.name, start_date, volumeid))

  def start_date(self, volumeid, start_date=None):
    '''Returns the volume start_date.

    When provided start_date argument will set the date first.
    '''
    with sqlite3.connect(self.pulldb,
                         detect_types=sqlite3.PARSE_DECLTYPES) as conn:
      if start_date:
        logging.debug('Setting start date for %d(%s).', volumeid, start_date)
        if isinstance(start_date, datetime):
          start_date = start_date.date()
        conn.execute('UPDATE pull_volumes SET start_date=? WHERE volume=?',
                     (start_date, volumeid))
      row = conn.execute(
        'SELECT start_date FROM pull_volumes WHERE volume=?', 
        (volumeid,)).fetchone()
    if row:
      return row[0]
    return date.min
    
  def volume_name(self, volumeid, name=None):
    '''Returns the volume name.

    When provided name argument will set the name first.
    '''
    with sqlite3.connect(self.pulldb,
                         detect_types=sqlite3.PARSE_DECLTYPES) as conn:
      if name:
        logging.debug('Setting name for volume %d(%s).', volumeid, name)
        conn.execute('UPDATE pull_volumes SET name=? WHERE volume=?',
                     (name, volumeid))
      row = conn.execute(
        'SELECT name FROM pull_volumes WHERE volume=?', 
        (volumeid,)).fetchone()
    if row:
      return row[0]

  def remove_volume(self, volumeid):
    'Removing a volume from the pull list.'
    logging.info('Removing %d and all related issues from pull list.', 
                 volumeid)
    with sqlite3.connect(self.pulldb) as conn:
      conn.execute(
        'DELETE FROM seen_issues WHERE volume=?', (volumeid,))
      conn.execute(
        'DELETE FROM pull_volumes WHERE volume=?', (volumeid,))

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

  def seen_issue(self, issueid, cvid=False):
    'Check whether an issue has been seen before.'
    logging.debug('Looking up issue id %d', issueid)
    seen = False
    column = 'issue'
    if cvid:
      column = 'cvid'
    with sqlite3.connect(self.pulldb) as conn:
      cursor = conn.execute(
        'SELECT %s FROM seen_issues WHERE issue=?' % (column,), (issueid,))
      result = cursor.fetchone()
      if result and result[0] == issueid:
        seen = True
    return seen

  def seen_issues(self, volumeid, cvid=False):
    'Return list of issues that have been seen for a particular volume.'
    if not volumeid:
      logging.debug('Looking up seen issues with no volume')
      condition = 'volume IS NULL'
      values = ()
    else:
      logging.debug('Looking up seen issues for volume %d', volumeid)
      condition = 'volume=?'
      values = (volumeid,)
    issues = []
    column = 'issue'
    if cvid:
      column = 'cvid'
    with sqlite3.connect(self.pulldb) as conn:
      cursor = conn.execute(
        'SELECT %s FROM seen_issues WHERE %s' % (column,condition), values)
      results = cursor.fetchall()
      if results:
        issues = [result[0] for result in results]
    return issues

  def volume_starts(self):
    'Return start dates for volumes.'
    start = {}
    with sqlite3.connect(self.pulldb, 
                         detect_types=sqlite3.PARSE_DECLTYPES) as conn:
      for (volume,start_date) in conn.execute(
        'SELECT volume,start_date FROM pull_volumes'):
        start[volume] = start_date or date.min
    return start

  def volumes(self):
    'Pulled volumes list generator. Returns ids only.'
    with sqlite3.connect(self.pulldb) as conn:
      for (volume,) in conn.execute('SELECT volume FROM pull_volumes'):
        yield volume
