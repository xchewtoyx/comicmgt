#!/usr/bin/python
# Copyright 2013 Russell Heilling
'''Sort a toread list against publication dates from the calibre database.'''
import logging
import re

from collections import defaultdict

import args

ISSUE_PATTERN = re.compile(r'(\d+) (.*)$')

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


class StreamClassifier(object):
  'Setup streams and provide interface to classify individual issues.'
  def __init__(self):
    self.volumes = {}
    self.volumes_seen = set()
    self.publishers = {}

  def _add_catchup_streams(self, stream_specs):
    'Add any catchup streams to the classifier.'
    for stream_spec in stream_specs:
      if ':' in stream_spec:
        stream, volumes = stream_spec.split(':')
        stream = stream.lower()
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

  def classify(self, metadata):
    'Identify which classifier stream matches an issue.'
    volume = metadata.identifiers.get('comicvine-volume')
    publisher = metadata.publisher
    if volume in self.volumes:
      self.volumes_seen.add(volume)
      return self.volumes[volume]
    if publisher in self.publishers:
      return self.publishers[publisher]
    return None

  def __del__(self):
    unseen_volumes = set(self.volumes.keys()) - self.volumes_seen
    if unseen_volumes:
      logging.info('The following catchup volumes were not seen: %s', 
                   ','.join(unseen_volumes))


def calculate_weights(streams):
  '''Calculate relative stream weights.'''
  lengths = [len(streams[stream]) for stream in streams]
  items = sum(lengths)
  max_stream = max(lengths)
  weight = {stream: len(streams[stream]) / (1.0 * max_stream) 
            for stream in streams}

  logging.debug('Total list items: %d', items)
  # Try and calculate interval.  With each loop, each stream will
  # contribute weight issues to progress It requires 1/weight loops
  # for a stream to contribute a whole issue so each stream will
  # contribute an issue approximately every 'sum(weights)/weight'
  # issues
  loop_issues = sum(weight.values())
  for stream in streams:
    if stream == 'ERRORS':
      # No nead for interval warning for errors
      continue
    if not weight[stream]:
      raise ValueError('Stream has weight of zero.  Will never yield issues.')
    interval = loop_issues / weight[stream]
    logging.info('Stream %s (issues/weight/interval): (%d/%0.4f/%d)', 
                  stream, len(streams[stream]), weight[stream], interval)
    # A stream contributing less that 1 in 20 issues is probably a
    # good indication that there are not enough issues for the stream
    # to be effective
    if interval > 20:
      logging.info('Stream %s has weight of %0.4f which will result in '
                   'significant gaps between issues (approx %0.1f issues). '
                   'Consider removing this stream or merging it with '
                   'another.', stream, weight[stream], interval)
  return weight


def merged_streams(streams):
  'Merge the sorted streams according to relative weights.'
  collected = defaultdict(float)

  weight = calculate_weights(streams)

  # Pass errors through first
  if 'ERRORS' in streams:
    for _, error in streams['ERRORS']:
      logging.info('Problem handling line: %s\n'
                   'Passing through to output unmodified', error)
      yield error.line
    del streams['ERRORS']

  while True:
    done = True
    
    # Least frequent streams are yielded first to minimise their
    # disruption from ideal position.
    for stream in sorted(streams, key=lambda stream: -weight[stream]):
      if streams[stream]:
        done = False
        collected[stream] += weight[stream]
        if collected[stream] >= 1.0:
          _, issue, title = streams[stream].pop(0)
          yield '%d %s' % (issue, title)
          collected[stream] -= 1.0
    if done:
      break
