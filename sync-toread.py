#!/usr/bin/python
# Copyright 2013 Russell Heilling
# pylint: disable=C0103,R0903
"""Sync items on toread list from calibre database into local folder.

Processes a toread file and exports the files for the first listed
titles listed into a local folder.

The toread file shold be in the format:

{comicvine_id} {title}

The content of the title field are not used.  This format is
compatible with todo.txt.
"""
from difflib import SequenceMatcher
import logging
from math import ceil, floor
import os
import re

from collections import OrderedDict

import args
from calibredb import CalibreDB, set_log_level
import logs

args.add_argument('--count', '-c', help='Number of issues to sync',
                  type=int, default='50')
args.add_argument('--toread', '-t', help='File containing issues to read',
                  type=bytes, default=None, required=True)
args.add_argument('--syncdir', '-d', help='Directory to sync issues to',
                  type=bytes, default=None, required=True)

ARGS = args.ARGS

class FormatChangeError(Exception):
  'Exception raised when attempt made to change format during rename'

class ReindexError(Exception):
  'Exception raised when reindexing is not possible'

class ToRead(OrderedDict):
  'Read matching lines from the toread file into an ordered dict'
  title_pattern = re.compile(r'^(\d+)\s+(.*)$')
  
  def __init__(self, toread_file, validator=None):
    super(ToRead, self).__init__()
    with open(toread_file, 'r') as toread:
      for title in toread:
        title_match = self.title_pattern.match(title)
        if title_match:
          if validator:
            try:
              validator(int(title_match.group(1)))
            except TypeError:
              # Raised when validator is not callable
              raise
            except Exception as err:
              logging.warn('IssueID not valid in line: %s', title)
              continue
          self[title_match.group(1)] = title_match.group(2)
          logging.debug('Found title %s(%s)', title_match.group(2), 
                        title_match.group(1))
        else:
          logging.info('Unmatching toread line: %s', title)


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
        if calibre_id not in self:
          logging.debug('Found file %s(%s)', entry, id_match.group(1))
          self[calibre_id] = entry

  def keep_files(self, keep_ids):
    'Remove any files that are not in the list of ids to keep.'
    for calibre_id, filename in self.items():
      if calibre_id not in keep_ids:
        logging.info('Removing file %s', filename)
        del self[calibre_id]

  def find_missing(self, wanted):
    'Return list of ids from wanted list for which there are no files present.'
    return list(set(wanted) - set(self.keys()))

def file_index(filename):
  'Find file index in filename if present.'
  index_match = re.match(r'(\d{4}(?:\.\d{2,3})?) ', filename)
  if index_match:
    index = index_match.group(1)
    return float(index)

def ordered_files(syncdir, toread):
  'Find the largest set of files in the correct order.'
  # Create a dict of files in syncdir with a valid index
  # In case of index clashes, the first candidate wins
  valid_files = {}
  for calibreid, filename in syncdir.items():
    index = file_index(filename)
    if index and index not in valid_files:
      valid_files[index] = calibreid
  # Create lists to compare to find the largest common sequence
  synclist = [valid_files[index] for index in sorted(valid_files.keys())]
  toreadlist = toread.keys()[:ARGS.count]
  logging.debug('Comparing %r and %r', synclist, toreadlist)
  # Use diffutils.SequenceMatcher to do the heavy lifting
  matcher = SequenceMatcher(None, toreadlist, synclist)
  ordered_ids = []
  for i, j, count in matcher.get_matching_blocks():
    ordered_ids.extend(toreadlist[i:i+count])
  logging.debug('Longest sorted subset: %r', ([
      syncdir[title] for title in ordered_ids],))
  return ordered_ids

def new_indexes(start, finish, titles):
  'Find new indexes for titles that fit between start and finish.'
  start = round(start, 3)
  finish = round(finish, 3)
  logging.debug('Inserting %d titles between %08.3f and %08.3f', 
                len(titles), start, finish)
  indexes = []
  if not finish:
    # Simplest case - just append titles with increasing integer indexes
    # Space is not an issue so leave gap for future reshuffles
    logging.debug('Appending %d titles to end of list', len(titles))
    finish = ceil(start) + 10 * len(titles)
  # Fit the titles between the start and finish with even spacing.
  # Round issues that are near an integer to the whole number to try
  # and avoid everything going fractional...
  interval = (finish - start) / (len(titles)+1)
  if finish <= start or interval < 1e-3:
    raise ReindexError('Unable in insert %d issues between %f and %f (%f)' % 
                       (len(titles), start, finish, interval))
  logging.debug('Stepping from %r to %r with interval %r', start, 
                finish, interval)
  index = start
  for title in titles:
    if floor(index)+1 < index+interval:
      # About to cross an integer boundary.  Align with the boundary.
      index = floor(index) + 1
    else:
      index += interval
    indexes.append('%08.3f' % index)
  return zip(indexes, titles)


def process_rename_queue(syncdir, toread, rename_queue):
  # Now handle the actual renaming
  for index, title in rename_queue:
    newname = '%s %s (%s).%s' % (index, toread[title], title, 
                                 syncdir.format[title])
    # Remove dangerous characters from title
    newname = re.sub(r'[:\'/"!]', r'_', newname)
    if syncdir[title] == newname:
      continue
    logging.info('Renaming %s to %s', syncdir[title], newname)
    try:
      syncdir[title] = newname
    except OSError:
      logging.warn(OSError)


def rename_files(syncdir, toread):
  'Rename files so that the filenames sort in todolist order.'
  # Get ordered files
  good_files = ordered_files(syncdir, toread)
  good_ratio = float(len(good_files)) / len(syncdir)
  level = logging.INFO
  if good_ratio < 0.5:
    level = logging.WARN
  logging.debug('%d good %d total', len(good_files), len(syncdir))
  logging.log(
    level, 'Renaming %.2f%% of files (%d/%d)',
    100*(1-good_ratio), len(syncdir) - len(good_files), len(syncdir))
  # iterate through todo items
  last_index = 0
  rename_queue = []
  reindex_queue = []
  for title in toread.keys()[:ARGS.count]:
    #  if item in good_files reindex any pending files
    if title in good_files:
      current_index = file_index(syncdir[title])
      logging.debug('File has suitable index, ignoring %s (i:%d)', 
                    syncdir[title], current_index)
      if reindex_queue:
        try:
          reindex_entries = new_indexes(last_index, current_index, 
                                        reindex_queue)
        except ReindexError as err:
          # If there is an error indexing the files, abort the attempt
          # to keep the same indexes and just renumber the rest of the
          # files.
          logging.error('Error reindexing files: %s', err.message)
          good_files = []
        else:
          logging.debug('New indices: %r', [
              (index, toread[title]) for index, title in reindex_entries])
          rename_queue.extend(reindex_entries)
          reindex_queue = []
      last_index = current_index
      continue
    else:
      logging.debug('Adding %s to reindex queue', syncdir[title])
      reindex_queue.append(title)
  # Append any remaning files in the reindex queue to the rename queue
  # These are going on the end so we can let new_indexes have as much
  # room as it wants
  if reindex_queue:
    rename_queue.extend(new_indexes(last_index, None, reindex_queue))
    
  process_rename_queue(syncdir, toread, rename_queue)

def main():
  'Read the toread list'
  calibredb = CalibreDB()
  toread = ToRead(ARGS.toread, validator=calibredb.issue)
  syncdir = ExportDirectory(ARGS.syncdir)

  # Grab the ids of the first count entries
  wanted = toread.keys()[:ARGS.count]

  # Remove any files not in the list
  syncdir.keep_files(wanted)

  # Export any files not already present
  calibredb.export_files(wanted, syncdir)

  # Rename files so they sort in reading list order
  rename_files(syncdir, toread)

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
