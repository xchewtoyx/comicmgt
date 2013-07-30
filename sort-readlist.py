#!/usr/bin/python

import logging
import re
import subprocess
import sys
import os

from collections import defaultdict

import calibre_config
from calibre.library.database2 import LibraryDatabase2
from calibre.utils.config import prefs

import args

ISSUE_PATTERN = re.compile('(\d+) (.*)$')

args.add_argument('--archive', '-a', help='Archive file before sorting',
                  action='store_true')
args.add_argument('--todobin', '-t', help='path to todo.txt script',
                  type=str, default='todo.sh')
args.add_argument('--infile', '-i', help='path to input file',
                  default=sys.stdin)
args.add_argument('--outfile', '-o', help='path to output file',
                  default=sys.stdout)
args.add_argument('--verbose', '-v', help='Enable verbose logging',
                  action='store_true')

ARGS={}

class StreamClassifier(object):
  def __init__(self):
    self.streams = ['catchup', 'marvel', 'dc', 'valiant']
    self.catchup_volumes = ['18436', '18519', '18520', '18521']

  def stream_catchup(self, mi):
    volume = mi.identifiers.get('comicvine-volume')
    return volume and volume in self.catchup_volumes
      
  def stream_marvel(self, mi):
    return mi.publisher in ['Marvel', 'Max']

  def stream_dc(self, mi):
    return mi.publisher in ['DC', 'DC Comics']

  def stream_valiant(self, mi):
    return mi.publisher in ['Valiant']

  def classify(self, mi):
    for stream in self.streams:
      classifier = getattr(self, 'stream_'+stream)
      if classifier and classifier(mi):
        return stream
    return None

def get_issues(infile):
  'Find issues listed in "id title" format.'
  for line in infile:
    issueid = ISSUE_PATTERN.match(line)
    if issueid:
      issue_id, issue_name = issueid.groups()
      logging.debug('Found issue "%s"(%d) [%s]', issue_id, issue_name)
      yield int(issue_id), issue_name
    else:
      logging.warn('Unable to parse line: %s', line)

def get_issue_details(infile):
  'Look up issue details in Calibre library.'
  db = LibraryDatabase2(prefs['library_path'])
  classifier = StreamClassifier()
  for issue, title in get_issues(infile):
    mi = db.get_metadata(issue, index_is_id=True)
    if mi:
      stream = classifier.classify(mi)
      logging.debug('Found issue %s(%d) [%s] [%s]', 
                    title, issue, stream, mi.pubdate)
      # Return tuple with first entry being a tuple of the sort keys
      yield (mi.pubdate, mi.title_sort), issue, title, stream
    else:
      logging.warn('Unable to find issue in database: %s(%d)', title, issue)

def get_streams(infile):
  streams = defaultdict(list)
  for sortkey, issue, title, stream in get_issue_details(infile):
    streams[stream].append((sortkey, issue, title))
  for stream in streams:
    streams[stream].sort()
  return streams

def merged_streams(infile):
  streams = get_streams(infile)
  items = sum([len(streams[stream]) for stream in streams])
  weight = {}

  for stream in streams:
    weight[stream] = len(streams[stream]) / (1.0 * items)

  for i in range(items):
    collected = defaultdict(float)
    for stream in streams:
      if streams[stream]:
        collected[stream] += weight[stream]
        if collected >= 1.0:
          yield streams[stream].pop(0)
          collected[stream] -= 1.0

  for stream in streams:
    if len(streams[stream]):
      for item in streams[stream]:
        yield item

def main():
  logger = logging.getLogger()
  if ARGS.verbose:
    logger.setLevel(logging.DEBUG)

  # archive todo list
  if ARGS.archive:
    try:
      output = subprocess.check_output([ARGS.todobin, 'archive'])
    except CalledProcessError as e:
      logging.error('Unable to archive old items: %s', e.output)

  # Open input and sort by pubdate then name
  infile = ARGS.infile
  if isinstance(infile, basestring):
    infile = open(infile, 'r')
  issues = list(merged_streams(infile))
  if infile is not sys.stdin:
    infile.close()
    
  # Write out sorted list
  outfile = ARGS.outfile
  if isinstance(outfile, basestring):
    outfile = open(outfile, 'w')
  for __, issue, title in issues:
    outfile.write('%d %s\n' % (issue, title))
  if outfile is sys.stdout:
    outfile.flush()
  else:
    outfile.close()

if __name__ == '__main__':
  ARGS = args.parse_args()
  main()
