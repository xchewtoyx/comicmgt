#!/usr/bin/python
# Copyright 2013 Russell Heilling.

from collections import defaultdict
import logging
import sys
import re

import args
import logs
from toread import ReadingList

import numpy

args.add_argument('--reference', '-r', help='Path to reference toread file.')
args.add_argument('--candidate', '-c', help='Path to candidate file.', 
                  default=None)
args.add_argument('--quiet', '-q', action='store_true',
                  help=('Do not print statistics.  Return will be '
                        'non-zero if thresholds are exceeded.'))
ARGS = args.ARGS

def enumerate_streams(titles):
  last_index = defaultdict(int)
  stream_intervals = defaultdict(list)
  stream_pattern = re.compile(r'\+([\w]+)(?:$|\s)')
  for index, (calibreid, title) in enumerate(titles):
    stream_match = stream_pattern.search(title)
    stream = ''
    if stream_match:
      stream = stream_match.group(1)
    logging.debug('Index: %d/%r/%s', index, stream, title)
    interval = index - last_index[stream]
    stream_intervals[stream].append(interval)
    last_index[stream] = index
  return stream_intervals

def stream_stats(titles):
  stats = {}
  stream_intervals = enumerate_streams(titles)
  for stream in stream_intervals:
    stats[stream] = numpy.array(stream_intervals[stream])
  return stats

def compare_stats(reference, candidate):
  # Implement thresholds
  # 1. Install if there are differences between the sets in the files
  new_streams = set(candidate.keys()) ^ set(reference.keys())
  if new_streams:
    return 'new stream encountered: %r' % new_streams
  # 2. Check each stream.  If the new.mean differs from ref.mean by
  # more than ref.std/2.
  for stream in reference:
    threshold = reference[stream].std()/2
    stream_variation = abs(candidate[stream].mean()-reference[stream].mean())
    if stream_variation > threshold:
      return 'Mean interval for stream %s exceeds threshold (%.03f/%.03f)' % (
        stream, stream_variation, threshold)

def main():
  reference = stream_stats(ReadingList(ARGS.reference).list_issues())
  for stream, data in reference.items():
    logging.info('%s: %d/%.03f/%.03f (len/avg/std)', stream, len(data), 
                 data.mean(), data.std())
  if ARGS.candidate:
    candidate = stream_stats(ReadingList(ARGS.candidate).list_issues())
    install_candidate = compare_stats(reference, candidate)
    if install_candidate:
      if not ARGS.quiet:
        print 'Threshold passed: %s' % install_candidate
      print 'OK'

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
