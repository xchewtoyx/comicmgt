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
args.add_argument(
  '--catchup_volumes', '-c', 
  help='Comma separated list of volume ids to put in the "catchup" stream.')

ARGS={}

class StreamClassifier(object):
  def __init__(self):
    self.streams = ['catchup', 'marvel', 'dc', 'valiant', 'rebellion']
    self.catchup_volumes = set(ARGS.catchup_volumes.split(','))
    self.catchup_seen = set()

  def stream_catchup(self, mi):
    volume = mi.identifiers.get('comicvine-volume')
    if volume and volume in self.catchup_volumes:
      self.catchup_seen.add(volume)
      return volume
      
  def stream_marvel(self, mi):
    return mi.publisher in ['Marvel', 'Max']

  def stream_dc(self, mi):
    return mi.publisher in ['DC', 'DC Comics']

  def stream_valiant(self, mi):
    return mi.publisher in ['Valiant']

  def stream_rebellion(self, mi):
    return mi.publisher in ['Rebellion']

  def classify(self, mi):
    for stream in self.streams:
      classifier = getattr(self, 'stream_'+stream)
      if classifier and classifier(mi):
        return stream
    return None

  def __del__(self):
    unseen_volumes = self.catchup_volumes - self.catchup_seen
    if unseen_volumes:
      logging.warn('The following catchup volumes were not seen: %r', 
                   unseen_volumes)

def get_issues(infile):
  'Find issues listed in "id title" format.'
  for line in infile:
    issueid = ISSUE_PATTERN.match(line)
    if issueid:
      issue_id, issue_name = issueid.groups()
      logging.debug('Found issue "%s"(%s)', issue_name, issue_id)
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
  lengths = [len(streams[stream]) for stream in streams]
  items = sum(lengths)
  max_stream = max(lengths)
  logging.debug('Total list items: %d', items)
  weight = {}

  for stream in streams:
    weight[stream] = len(streams[stream]) / (1.0 * max_stream)
    logging.debug('Stream length[%s]: %d', stream, len(streams[stream]))
    logging.debug('Stream weight[%s]: %0.4f', stream, weight[stream])

  collected = defaultdict(float)
  while True:
    done = True
    for stream in streams:
      if streams[stream]:
        done = False
        collected[stream] += weight[stream]
        if collected[stream] >= 1.0:
          yield streams[stream].pop(0)
          collected[stream] -= 1.0
    if done:
      break

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
