#!/usr/bin/python
# Copyright 2013 Russell Heilling
'''Access data for comics stored in calibre.'''
import logging
import sys

# Calibre modules cannot be loaded outside the calibre environment so disable
# style errors caused by failing imports
import calibre_config                                  #pylint: disable=W0611
from calibre.library.database2 import LibraryDatabase2 #pylint: disable=F0401
from calibre.utils.config import prefs                 #pylint: disable=F0401

class CalibreDB(LibraryDatabase2):
  '''Interface to the calibre database.

  targeted for comics stored in calibre and tagged with comicvine metadata.
  '''
  def __init__(self):
    LibraryDatabase2.__init__(self, prefs['library_path'])

  def issue(self, issueid):
    'Retrieve an issue by calibre id'
    metadata = self.get_metadata(issueid, index_is_id=True)
    if metadata:
      logging.debug('Found issue %s (%d) [%s/%s]', 
                    metadata.title, issueid, metadata.pubdate, 
                    metadata.publisher)
      return metadata
    return None

  def volume(self, volumeid):
    'Retrieve data on a volume by comicvine volume id'
    pass

def main(issues):
  'If run as a script identify issues provided as arguments.'
  calibredb = CalibreDB()
  for issue in issues:
    issue_data = calibredb.issue(int(issue))
    if issue_data:
      print 'Found issue %s(%s) [%s/%s] {%s}' % (
        issue_data.title, issue, issue_data.pubdate, issue_data.publisher,
	issue_data.identifiers)
    else:
      print 'No issue found with id %s' % issue

if __name__ == '__main__':
  main(sys.argv[1:])
