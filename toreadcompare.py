#!/usr/bin/python
# Copyright 2013 Russell Heilling.

from collections import defaultdict
import logging
import sys
import re

import args
import logs
from toread import ReadingList

from numpy import array, mean, median, std

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
  stream_pattern = re.compile(r'\s\+([\w]+)(?:$|\s)')
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
    stats[stream] = array(stream_intervals[stream])
  for stream, data in stats.items():
    logging.info('%s: %d/%.03f/%.03f/%.03f (len/avg/median/std)', 
                 stream, len(data), mean(data), median(data), std(data))
  return stats

def compare_stats(reference, candidate):
  # Implement thresholds
  # 1. Install if there are differences between the sets in the files
  new_streams = set(candidate.keys()) ^ set(reference.keys())
  if new_streams:
    return 'Stream differences encountered: %r' % new_streams
  # 2. Check each stream.  Install the candidate if candidate.median
  # differs from reference.mean by more than 0.675 * reference.std.
  # In a normal distribution 50% of samples are within 0.675
  # sigma. For this to hold true the median must be somewhere in the
  # -0.675s<median<0.675s range.  If the new median is outside this
  # range then it is pretty clear that the distribution is skewed and
  # a resort is needed.
  for stream in reference:
    threshold = 0.675 * reference[stream].std()
    stream_variation = abs(median(candidate[stream])-
                           mean(reference[stream]))
    if stream_variation > threshold:
      return (
        'Median interval for stream %s exceeds threshold (%.03f/%.03f)' % (
          stream, stream_variation, threshold))

def main():
  logging.info('Processing reference file (%r)', ARGS.reference)
  reference = stream_stats(ReadingList(ARGS.reference).list_issues())
  if ARGS.candidate:
    logging.info('Processing candidate file (%r)', ARGS.candidate)
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
