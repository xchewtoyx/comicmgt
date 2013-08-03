#!/usr/bin/python

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
  oldindex = re.compile(r'(\d{4}) ')
  filetype = re.compile(r'.*\.(cb[rz])$')
  index = 0
  seen_idx = []
  for title in titles:
    index += 1
    idx = oldindex.match(files[title])
    if idx:
      file_index = int(idx.group(1))
      if file_index >= index and file_index not in seen_idx:
        logging.debug('File has suitable index, ignoring %s (i:%d, s:%r)', 
                      files[title], index, seen_idx)
        seen_idx.append(file_index)
        index = file_index
        continue
      logging.debug('File has unsuitable index, renaming %s (i:%d, s:%r)', 
                    files[title], index, seen_idx)
    file_ext = filetype.match(files[title]).group(1)
    newname = '%04d %s (%s).%s' % (
      index, titles[title], title, file_ext)
    newname = re.sub(r'[\'/"!]', r'_', newname)
    logging.debug('Renaming %s to %s', files[title], newname)
    try:
      os.rename(os.path.join(ARGS.syncdir, files[title]),
                os.path.join(ARGS.syncdir, newname))
    except OSError as e:
      logging.error('Error renaming file %s -> %s: %r', files[title], newname, e)
    seen_idx.append(index)

def main():
  logger = logging.getLogger()
  if ARGS.verbose:
    logger.setLevel(logging.DEBUG)
  toread = get_titles()
  have_files = get_files()
  remove_old_files(have_files, toread)
  export_files(toread, have_files)
  have_files = get_files()
  rename_files(have_files, toread)

if __name__ == '__main__':
  ARGS = args.parse_args()
  main()
