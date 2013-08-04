#!/usr/bin/python
<<<<<<< HEAD
=======
# pylint: disable=C0103,R0903
"""Sync items on toread list from calibre database into local folder.
>>>>>>> Added some comments.  Removed need to pass wanted to rename_files()

import logging
import os
import re
import sys

from collections import OrderedDict

import calibre_config
from calibre.library.database2 import LibraryDatabase2
from calibre.library.save_to_disk import save_to_disk
from calibre.utils.config import prefs

import args

ARGS = None
args.add_argument('--count', '-c', help='Number of issues to sync',
                  type=int, default='50')
args.add_argument('--toread', '-t', help='File containing issues to read',
                  type=bytes, default=None, required=True)
args.add_argument('--syncdir', '-d', help='Directory to sync issues to',
                  type=bytes, default=None, required=True)
args.add_argument('--verbose', '-v', help='Verbose logging',
                  default=False, action='store_true')

<<<<<<< HEAD
class ExportFile(object):
  'Settings to use when exporting files'
  asciiize = True
  formats = 'all'
  replace_whitespace = False
  save_cover = False
  single_dir = True
  template = '{pubdate} {title} ({id})'
  timefmt = '%Y%m%d'
  to_lowercase = False
  update_metadata = False
  write_opf = False

def get_titles():
  title_pattern = re.compile(r'^(\d+)\s+(.*)$')
  titles = OrderedDict()
  toread = open(ARGS.toread, 'r')
  for title in toread:
    title_match = title_pattern.match(title)
    if title_match:
      titles[title_match.group(1)] = title_match.group(2)
      logging.debug(
        'Found title %s(%s)', title_match.group(2), title_match.group(1))
    if len(titles) >= ARGS.count:
      break
  return titles
    

def get_files():
  title_pattern = re.compile(r'\((\d+)\).cb[rz]')
  files = {}
  for entry in os.listdir(ARGS.syncdir):
    id_match = title_pattern.search(entry)
    if id_match:
      files[id_match.group(1)] = entry
      logging.debug('Found file %s(%s)', entry, id_match.group(1))
  return files


def remove_old_files(files, toread):
  for calibre_id, filename in files.items():
    if calibre_id not in toread:
      logging.info('Removing file %s', filename)
      os.remove(os.path.join(ARGS.syncdir, filename))


def rename_synced(files, toread):
  for calibre_id, filename in files.items():
    if calibre_id in toread:
      logging.debug('Already have title %s(%s)', filename, calibre_id)
      del toread[calibre_id]


def export_files(titles, have_files):
  def export_progress(calibre_id, title, failed, traceback):
    if failed:
      logging.error('Unable to export %s(%s): %s',
                    title, calibre_id, traceback)
    else:
      logging.debug('Exported %s(%s)', title, calibre_id)
    return not(failed)

  db = LibraryDatabase2(prefs['library_path'])
  opts = ExportFile()
  ids = [int(id) for id in list(set(titles.keys())-set(have_files.keys()))]
  logging.info('Exporting %d titles...', len(ids))
  logging.debug('%s', repr(titles.keys()))
  failures = save_to_disk(
    db, ids, ARGS.syncdir, opts=opts, callback=export_progress)
  if failures:
    logging.warn('Unable to export files: %s', repr(failures))

def rename_files(files, titles):
=======
class FormatChangeError(Exception):
  'Exception raised when attempt made to change format during rename'
  pass

class ToRead(OrderedDict):
  'Read matching lines from the toread file into an ordered dict'
  title_pattern = re.compile(r'^(\d+)\s+(.*)$')
  
  def __init__(self, toread_file):
    super(ToRead, self).__init__()
    with open(toread_file, 'r') as toread:
      for title in toread:
        title_match = self.title_pattern.match(title)
        if title_match:
          self[title_match.group(1)] = title_match.group(2)
          logging.debug('Found title %s(%s)', title_match.group(2), 
                        title_match.group(1))
        else:
          logging.warn('Unmatching toread line: %s', title)


class CalibreDatabase(LibraryDatabase2):
  'Operate on calibre database'
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


class ExportDirectory(dict):
  'Files present in the export directory'
  title_pattern = re.compile(r'\((\d+)\).(cb[rz])')

  def __init__(self, directory):
    super(ExportDirectory, self).__init__()
    self.directory = directory
    self.format = {}
    self.scan()

  def __delitem__(self, key):
    if os.path.exists(os.path.join(self.directory, self[key])):
      try:
        os.remove(os.path.join(self.directory, self[key]))
      except OSError as err:
        logging.error('Error removing file %s: %s', self[key], err)
    super(ExportDirectory, self).__delitem__(key)
    del self.format[key]

  def __setitem__(self, key, value):
    title_match = self.title_pattern.search(value)
    if not title_match:
      raise ValueError('Cannot find ID and extension for file %s' % value)
    calibre_id = title_match.group(1)
    if key != calibre_id:
      raise KeyError(
        'Calibre ID in file(%s) does not match specified key(%s)' % (
          calibre_id, key))

    # Setting a key that exists should rename the file
    if key in self and os.path.exists(os.path.join(self.directory, 
                                                   self[key])):
      if self[calibre_id] == value:
        logging.debug('Skipping rename, destination same as source: %s', 
                      self[calibre_id])
        return
      if not value.endswith(self.format[calibre_id]):
        raise FormatChangeError(
          'Attempt to change format during rename (%s does not have '
          'format %s).', value, self.format[calibre_id])
      logging.debug('Renaming %s to %s', self[key], value)
      try:
        os.rename(os.path.join(self.directory, self[key]),
                  os.path.join(self.directory, value))
      except OSError as err:
        raise OSError ('Error renaming file %s -> %s: %s', 
                       self[key], value, err)
    elif not os.path.exists(os.path.join(self.directory, value)):
      raise ValueError('File %s does not exist' % value)

    super(ExportDirectory, self).__setitem__(key, value)
    self.format[key] = title_match.group(2)

  def scan(self):
    'Scan the export directory for files'
    for key in self:
      if not os.path.exists(os.path.join(self.directory, self[key])):
        del self[key]
    for entry in os.listdir(self.directory):
      id_match = self.title_pattern.search(entry)
      if id_match:
        calibre_id = id_match.group(1)
        self[calibre_id] = entry
        logging.debug('Found file %s(%s)', entry, id_match.group(1))

  def keep_files(self, keep_ids):
    'Remove any files that are not in the list of ids to keep.'
    for calibre_id, filename in self.items():
      if calibre_id not in keep_ids:
        logging.info('Removing file %s', filename)
        del self[calibre_id]

  def find_missing(self, wanted):
    'Return list of ids from wanted list for which there are no files present.'
    return list(set(wanted) - set(self.keys()))


def rename_files(syncdir, toread):
  'Rename files so that the filenames sort in todolist order.'
>>>>>>> Added some comments.  Removed need to pass wanted to rename_files()
  oldindex = re.compile(r'(\d{4}) ')
  index = 0
  seen_idx = []
  for title in wanted:
    if title not in syncdir:
      # Entry has not been synced, end of loop
      break
    index += 1
    idex_match = oldindex.match(syncdir[title])
    if index_match:
      file_index = int(index_match.group(1))
      
      if file_index >= index and file_index not in seen_idx:
        logging.debug('File has suitable index, ignoring %s (i:%d, s:%r)', 
                      syncdir[title], index, seen_idx)
        seen_idx.append(file_index)
        index = file_index
        continue
      logging.debug('File has unsuitable index, renaming %s (i:%d, s:%r)', 
                    syncdir[title], index, seen_idx)
    newname = '%04d %s (%s).%s' % (index, toread[title], title, 
                                   syncdir.format[title])
    # Remove dangerous characters from title
    newname = re.sub(r'[\'/"!]', r'_', newname)
    logging.debug('Renaming %s to %s', syncdir[title], newname)
    try:
<<<<<<< HEAD
      os.rename(os.path.join(ARGS.syncdir, files[title]),
                os.path.join(ARGS.syncdir, newname))
    except OSError as e:
      logging.error('Error renaming file %s -> %s: %r', files[title], newname, e)
=======
      syncdir[title] = newname
    except OSError:
      logging.warn(OSError)
>>>>>>> Added some comments.  Removed need to pass wanted to rename_files()
    seen_idx.append(index)

def main():
  logger = logging.getLogger()
  if ARGS.verbose:
    logger.setLevel(logging.DEBUG)

  toread = ToRead(ARGS.toread)
  syncdir = ExportDirectory(ARGS.syncdir)
  calibredb = CalibreDatabase()

  # Grab the ids of the first count entries
  wanted = toread.keys()[:ARGS.count]

  # Remove any files not in the list
  syncdir.keep_files(wanted)

  # Export any files not already present
  calibredb.export_files(wanted, syncdir)

  # Rename files so they sort in reading list order
  rename_files(syncdir, toread)

if __name__ == '__main__':
  ARGS = args.parse_args()
  main()
