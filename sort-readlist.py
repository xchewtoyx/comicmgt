#!/usr/bin/python
# Copyright 2013 Russell Heilling
# pylint: disable=C0103
'''Sort a toread list against publication dates from the calibre database.'''
import logging
import re
import subprocess
import sys

from collections import defaultdict

# Calibre modules cannot be loaded outside the calibre environment so disable
# errors caused by failing imports
import calibre_config                                  #pylint: disable=W0611
from calibre.library.database2 import LibraryDatabase2 #pylint: disable=F0401
from calibre.utils.config import prefs                 #pylint: disable=F0401

import args

ISSUE_PATTERN = re.compile(r'(\d+) (.*)$')

args.add_argument('--archive', '-a', help='Archive file before sorting',
                  action='store_true')
args.add_argument('--todobin', '-t', help='path to todo.txt script',
                  type=str, default='todo.sh')
args.add_argument('--infile', '-i', help='path to input file',
                  default=sys.stdin)
args.add_argument('--outfile', '-o', help='path to output file',
                  default=sys.stdout)
args.add_argument('--verbose', '-v', help='Enable verbose logging',
                  action='count')
args.add_argument(
  '--publisher', '-p', action='append',
  help='Add a dedicated stream all issues from a specific publisher that '
       'are not part of a catchup stream. Can be comma separated to group '
       'imprints together (e.g --publisher marvel,max)')
args.add_argument(
  '--catchup_stream', '-c', action='append', 
  help=('Comma separated list of volume ids to put in the "catchup" stream.'
        'e.g. --catchup_stream ss:18436,18519,18520 to create a stream named '
        'ss with volumes'))

ARGS = args.ARGS

class LineError(Exception):
  def __init__(self, line):
    self.line = line
    super(LineError, self).__init__()

  def __str__(self):
    return 'Unable to parse line: %s' % self.line
    
class DatabaseError(Exception):
  def __init__(self, issue, title):
    self.issue = issue
    self.title = title
    self.line = '%d %s' % issue, title
    super(DatabaseError, self).__init__()

  def __str__(self):
    return 'Unable to find issue in database: %s(%d)' % (
      self.title, self.issue)

class StreamClassifier(object):
  def __init__(self):
    self.volumes = {}
    self.volumes_seen = set()
    self.publishers = {}

    if ARGS.catchup_stream:
      for stream_spec in ARGS.catchup_stream:
        if ':' in stream_spec:
          stream, volumes = stream_spec.split(':')
          for volume in volumes.split(','):
            if volume in self.volumes:
              raise ValueError('Duplicate volume detected in '
                               'catchup volumes: %s' % volume)
            self.volumes[volume] = stream
        else:
          raise ValueError('Invalid stream definition: %s', stream_spec)
    if ARGS.publisher:
      for stream_spec in ARGS.publisher:
        publishers = stream_spec.split(',')
        stream = publishers[0].lower()
        for publisher in publishers:
          if publisher in self.publishers:
            raise ValueError('Duplicate publisher detected in '
                             'publishers: %s' % publisher)
          self.publishers[publisher] = stream

  def classify(self, mi):
    volume = mi.identifiers.get('comicvine-volume')
    publisher = mi.publisher
    if volume in self.volumes:
      return self.volumes[volume]
    if publisher in self.publishers:
      return self.publishers[publisher]
    return None

  def __del__(self):
    unseen_volumes = set(self.volumes.keys()) - self.volumes_seen
    if unseen_volumes:
      logging.info('The following catchup volumes were not seen: %s', 
                   ','.join(unseen_volumes))

def get_issues(infile):
  'Find issues listed in "id title" format.'
  for line in infile:
    line = line.strip()
    issueid = ISSUE_PATTERN.match(line)
    if issueid:
      issue_id, issue_name = issueid.groups()
      logging.debug('Found issue "%s"(%s)', issue_name, issue_id)
      yield (int(issue_id), issue_name), None
    else:
      yield None, LineError(line)

def get_issue_details(infile):
  'Look up issue details in Calibre library.'
  db = LibraryDatabase2(prefs['library_path'])
  classifier = StreamClassifier()
  for issue_data, error in get_issues(infile):
    if error:
      yield issue_data, error
      continue
    issue, title = issue_data
    mi = db.get_metadata(issue, index_is_id=True)
    if mi:
      stream = classifier.classify(mi)
      logging.debug('Found issue %s(%d) [%s] [%s]', 
                    title, issue, stream, mi.pubdate)
      # Return tuple with first entry being a tuple of the sort keys
      yield ((mi.pubdate, mi.title_sort), issue, title, stream), None
    else:
      yield None, DatabaseError(issue, title)

def get_streams(infile):
  streams = defaultdict(list)
  for issue_details, error in get_issue_details(infile):
    if error:
      # Keep errors in relative order by using length of errors list
      # as sort key
      streams['errors'].append(((len(streams['errors']),), error))
      continue
    sortkey, issue, title, stream = issue_details
    streams[stream].append((sortkey, issue, title))
  for stream in streams:
    streams[stream].sort()
  return streams


def calculate_weights(streams):
  '''Calculate relative stream weights.'''
  lengths = [len(streams[stream]) for stream in streams]
  items = sum(lengths)
  max_stream = max(lengths)
  weight = {stream: len(streams[stream]) / (1.0 * max_stream) 
            for stream in streams}

  logging.debug('Total list items: %d', items)
  # try and calculate interval in each loop, each stream will
  # contribute 1/weight issues to progress It requires 1/weight loops
  # for a stream to contribute a whole issue so each stream will
  # contribute an issue every '1/weight * sum(1/weight[s] for s in
  # streams)' issues
  loop_issues = sum(1/weight[stream] for stream in streams)
  for stream in streams:
    # A stream contributing less that 1 in 20 issues is probably a
    # good indication that there are not enough issues for the stream
    # to be effective
    if not weight[stream]:
      raise ValueError('Stream has weight of zero.  Will never yield issues.')
    interval = loop_issues / weight[stream]
    if interval > 20:
      logging.info('Stream %s has weight of %0.4f which will result in '
                   'significant gaps between issues (approx %0.1f issues). '
                   'Consider removing this stream or merging it with '
                   'another.', stream, weight[stream], interval)
    logging.debug('Stream length[%s]: %d', stream, len(streams[stream]))
    logging.debug('Stream weight[%s]: %0.4f', stream, weight[stream])
    return weight


def merged_streams(infile):
  streams = get_streams(infile)
  collected = defaultdict(float)

  weight = calculate_weights(streams)

  # Pass errors through first
  if 'errors' in streams:
    for sortkey, error in streams['errors']:
      logging.info('Problem handling line: %s\n'
                   'Passing through to output unmodified', error)
      yield error.line
    del streams['errors']

  while True:
    done = True
    
    # Least frequent streams are yielded first to minimise their
    # disruption from ideal position.
    for stream in sorted(streams, key=lambda stream: -weight[stream]):
      if streams[stream]:
        done = False
        collected[stream] += weight[stream]
        if collected[stream] >= 1.0:
          sortkey, issue, title = streams[stream].pop(0)
          yield '%d %s' % (issue, title)
          collected[stream] -= 1.0
    if done:
      break

def main():
  logger = logging.getLogger()
  if ARGS.verbose:
    if ARGS.verbose >= 2:
      logger.setLevel(logging.DEBUG)
    else:
      logger.setLevel(logging.INFO)

  # archive todo list
  if ARGS.archive:
    try:
      output = subprocess.check_output([ARGS.todobin, 'archive'])
    except subprocess.CalledProcessError as error:
      logging.error('Unable to archive old items: %s', error.output)
    logging.info('Archive successful: %s', output)

  # Open input and sort by pubdate then name
  infile = ARGS.infile
  if isinstance(infile, basestring):
    infile = open(infile, 'r')
  lines = list(merged_streams(infile))
  if infile is not sys.stdin:
    infile.close()
    
  # Write out sorted list
  outfile = ARGS.outfile
  if isinstance(outfile, basestring):
    outfile = open(outfile, 'w')
  outfile.write('\n'.join(lines))
  if outfile is sys.stdout:
    outfile.flush()
  else:
    outfile.close()

if __name__ == '__main__':
  ARGS = args.parse_args()
  main()
