#!/usr/bin/python
# Copyright 2013 Russell Heilling
'''Sort a toread list against publication dates from the calibre database.'''
import logging
import re

from collections import defaultdict

import args
from calibredb import CalibreDB

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
  'Exception caused by a line which doesn\'t parse.'
  def __init__(self, line):
    super(LineError, self).__init__()
    self.line = line

  def __str__(self):
    return 'Unable to parse line: %s' % self.line
    

class DatabaseError(Exception):
  'Exception caused by an issue which isn\'t in the database.'
  def __init__(self, line):
    super(DatabaseError, self).__init__()
    self.line = line

  def __str__(self):
    return 'Unable to find issue in database: %s' % self.line


class BaseStream(list):
  'A Stream.'
  def __init__(self, name):
    super(BaseStream, self).__init__()
    self.name = name.replace(' ', '_')


class ErrorStream(BaseStream):
  'A class to hold any entries for which there are problems'
  name = 'ERRORS'


class IssueStream(BaseStream):
  'A Stream of issues.'
  issue_count = 0
  max_stream_size = 0

  def append(self, metadata):
    'Add an issue to the stream.'
    super(IssueStream, self).append(metadata)
    type(self).issue_count += 1
    if len(self) > self.max_stream_size:
      type(self).max_stream_size = len(self)
      logging.debug('New heavy hitter %s (%d)', self.name, len(self))

  @property
  def interval(self):
    'How many issues will there be between entries when merged?'
    return self.issue_count / (1.0 * len(self))

  @property
  def weight(self):
    'The relative weight of the stream.'
    weight = len(self) / (1.0 * self.max_stream_size)
    return weight



class StreamClassifier(object):
  'Setup streams and provide interface to classify individual issues.'
  issue_pattern = re.compile(r'(\d+) (.*)$')

  def __init__(self):
    self.volumes = {}
    self.volumes_seen = set()
    self.publishers = {}
    self.streams = {
      None: IssueStream('default'),
    }
    self.errors = ErrorStream()
    self.calibredb = CalibreDB()

  def _add_catchup_streams(self, stream_specs):
    'Add any catchup streams to the classifier.'
    for stream_spec in stream_specs:
      if ':' in stream_spec:
        stream, volumes = stream_spec.split(':')
        stream = stream.lower()
        self.streams[stream] = IssueStream(stream)
        for volume in volumes.split(','):
          if volume in self.volumes:
            raise ValueError('Duplicate volume detected in '
                             'catchup volumes: %s' % volume)
          self.volumes[volume] = stream
      else:
        raise ValueError('Invalid stream definition: %s', stream_spec)

  def _add_publisher_streams(self, publisher_specs):
    'Add any publisher streams to the classifier'
    for stream_spec in publisher_specs:
      publishers = stream_spec.split(',')
      stream = publishers[0].lower()
      self.streams[stream] = IssueStream(stream)
      for publisher in publishers:
        if publisher in self.publishers:
          raise ValueError('Duplicate publisher detected in '
                           'publishers: %s' % publisher)
        self.publishers[publisher] = stream

  def add_streams(self, catchup_streams=None, publisher_streams=None):
    'Add defined streams to the classifier.'
    if catchup_streams:
      self._add_catchup_streams(catchup_streams)
    if publisher_streams:
      self._add_publisher_streams(publisher_streams)

  def identify(self, line):
    'Take an input line and classify it.'
    line = line.strip()
    try:
      match = self.issue_pattern.match(line)
      if not match:
        raise LineError(line)
      issue = match.group(1)
      metadata = self.calibredb.issue(int(issue))
      if not metadata:
        raise DatabaseError(line)
      self.classify(metadata)
    except (LineError, DatabaseError) as error:
      logging.info('%s', error)
      self.errors.append(error)

  def classify(self, metadata):
    'Identify which classifier stream matches an issue.'
    volume = metadata.identifiers.get('comicvine-volume')
    publisher = metadata.publisher
    self.volumes_seen.add(volume)
    if volume in self.volumes:
      stream = self.volumes[volume]
    elif publisher in self.publishers:
      stream = self.publishers[publisher]
    else:
      stream = None
    self.streams[stream].append(metadata)

  def __del__(self):
    unseen_volumes = set(self.volumes.keys()) - self.volumes_seen
    if unseen_volumes:
      logging.info('The following catchup volumes were not seen: %s', 
                   ','.join(unseen_volumes))

  def merged_streams(self):
    'Merge the sorted streams according to relative weights.'
    subtitle_match = re.compile(r':[^#]+$')
    collected = defaultdict(float)
    yielded = defaultdict(int)

    # Pass errors through first
    for error in self.errors:
      logging.info('Problem handling line: %s\n'
                   'Passing through to output unmodified', error)
      yield error.line

    # Sort streams in ascending weight order.  By yielding the least
    # frequent streams first we minimise their disruption from ideal
    # position.
    streams = sorted(self.streams.values(), key=lambda stream: -stream.weight)

    # Log stream stats
    for stream in streams:
      logging.info('Stream stats for %s (length/weight/interval): '
                   '%d/%0.4f/%0.4f', stream.name, len(stream), stream.weight,
                   stream.interval)

    while True:
      done = True
    
      for stream in streams
        if not stream.weight:
          raise ValueError('Weight for stream %s is zero.  '
                           'Will never yield issues.' % stream.name)
        if yielded[stream.name] < len(stream):
          done = False
          collected[stream.name] += stream.weight
          if collected[stream.name] - yielded[stream.name] >= 1.0:
            metadata = stream[yielded[stream.name]]
            title = re.sub(subtitle_match, '', metadata.title)
            yield '%d %s +%s' % (metadata.id, title, stream.name)
            yielded[stream.name] += 1
      if done:
        break
