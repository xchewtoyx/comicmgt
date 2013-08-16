#!/usr/bin/python
# Copyright 2013 Russell Heilling
'''Access data for comics stored in calibre.'''
import logging
import sys

# Calibre modules cannot be loaded outside the calibre environment so disable
# style errors caused by failing imports
import calibre_config                                  #pylint: disable=W0611
import calibre.constants                               #pylint: disable=F0401
from calibre.library.database2 import LibraryDatabase2 #pylint: disable=F0401
from calibre.library.save_to_disk import save_to_disk  #pylint: disable=F0401
from calibre.utils.config import prefs                 #pylint: disable=F0401
import calibre.utils.logging as calibre_logging        #pylint: disable=F0401

# Some modules get a copy of calibre.constants.DEBUG before we can set
# it false. Override them here
sys.modules[save_to_disk.__module__].DEBUG = False

class CalibreDB(LibraryDatabase2):
  '''Interface to the calibre database.

  targeted for comics stored in calibre and tagged with comicvine metadata.
  '''
  class ExportFile(object):
    'Options for exporting files from library'
    # This class is a pure namespace so ignore the fact there are no methods
    # pylint: disable=R0903
    asciiize = True
    formats = 'cbr,cbz'
    replace_whitespace = False
    save_cover = False
    single_dir = True
    template = '{pubdate} {title} ({id})'
    timefmt = '%Y%m%d'
    to_lowercase = False
    update_metadata = False
    write_opf = False

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

  def export_files(self, titles, syncdir):
    'Export selected ids to specified directory'
    def export_progress(calibre_id, title, failed, traceback):
      'Callback used for progress updates during the export operation.'
      if failed:
        logging.error('Unable to export %s(%s): %s',
                      title, calibre_id, traceback)
      else:
        logging.debug('Exported %s(%s)', title, calibre_id)
      return not(failed)

    opts = self.ExportFile()
    ids = [int(idx) for idx in list(set(titles)-set(syncdir.keys()))]
    logging.info('Exporting %d titles...', len(ids))
    failures = save_to_disk(
      self, ids, syncdir.directory, opts=opts, callback=export_progress)
    # Callback does not recieve the filename, so rather than updating
    # syncdir as files are added we need to rescan once the export is
    # complete...
    syncdir.scan()
    if failures:
      logging.warn('Unable to export files: %s', repr(failures))


def set_log_level(level):
  '''Set default log level.

  Translates from standard logging levels to calibre equivalents.
  '''
  level_map = {
    logging.DEBUG: calibre_logging.DEBUG,
    logging.INFO: calibre_logging.INFO,
    logging.WARN: calibre_logging.WARN,
    logging.ERROR: calibre_logging.ERROR,
    logging.CRITICAL: calibre_logging.ERROR,
    }
  # Scripts that use this module usually use calibre-debug to setup
  # the environment.  This has the side effect of automatically
  # enabling certain debug messages.  Try to turn these off if running
  # at non-debug log level.
  if level == logging.DEBUG:
    calibre.constants.DEBUG = True
  else:
    calibre.constants.DEBUG = False
  level = level_map[level]
  calibre_logging.default_log = calibre_logging.Log(
    level=level)


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

