#!/usr/bin/python

import logging
import os
import re
import sys

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
  template = '{title} ({id})'
  timefmt = None
  to_lowercase = False
  update_metadata = False
  write_opf = False

def get_titles():
  title_pattern = re.compile(r'^(\d+)\s+(.*)$')
  titles = {}
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


def remove_synced(files, toread):
  for calibre_id, filename in files.items():
    if calibre_id in toread:
      logging.debug('Already have title %s(%s)', filename, calibre_id)
      del toread[calibre_id]


def sync_files(titles):
  def export_progress(calibre_id, title, failed, traceback):
    if failed:
      logging.error('Unable to export %s(%s): %s',
                    title, calibre_id, traceback)
    else:
      logging.debug('Exported %s(%s)', title, calibre_id)
    return not(failed)

  db = LibraryDatabase2(prefs['library_path'])
  opts = ExportFile()
  ids = [int(calibre_id) for calibre_id in titles.keys()]
  logging.info('Exporting %d titles...', len(ids))
  logging.debug('%s', repr(titles.keys()))
  failures = save_to_disk(
    db, ids, ARGS.syncdir, opts=opts, callback=export_progress)
  if failures:
    logging.warn('Unable to export files: %s', repr(failures))

def main():
  logger = logging.getLogger()
  if ARGS.verbose:
    logger.setLevel(logging.DEBUG)
  toread = get_titles()
  have_files = get_files()
  remove_old_files(have_files, toread)
  remove_synced(have_files, toread)
  sync_files(toread)

if __name__ == '__main__':
  ARGS = args.parse_args()
  main()
