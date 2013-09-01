#!/usr/bin/python
# Copyright 2013 Russell Heilling
# pylint: disable=C0103
'''Comic toread list management.

Manage titles on toread list.
'''
import logging
import os
import re

from calibredb import CalibreDB

class ReadingList(object):
  'Manage todo.txt style reading list.'
  issue_pattern = re.compile(r'(\d+) (.*)$')

  def __init__(self, readinglist):
    self.readinglist = readinglist
    self.calibredb = CalibreDB()

  def add_issues(self, issues):
    'Append an issue to the reading list.'
    with open(self.readinglist, 'a') as reading_file:
      for issue in issues:
        reading_file.write('%d %s\n' % issue)

  def list_issues(self, as_metadata=False):
    'Generate list of issues in toread list'
    with open(self.readinglist, 'r') as reading_file:
      for line in reading_file:
        issue_match = self.issue_pattern.match(line)
        if issue_match:
          issueid = int(issue_match.group(1))
          if as_metadata:
            yield self.calibredb.issue(issueid)
          else:
            yield (issueid, issue_match.group(2))

  def list_volumes(self):
    'Generate list of volumes in toread list'
    volumes = set()
    for issue in self.list_issues(as_metadata=True):
      volumeid = int(issue.identifiers.get('comicvine-volume'))
      if volumeid:
        volumes.add((volumeid, issue.series))
    for volume in volumes:
      yield volume
