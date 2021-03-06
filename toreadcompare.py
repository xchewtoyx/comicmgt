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
                  action='append')
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
    logging.info('[%s]: %d/%.03f/%.03f/%.03f/%0.3f (len/avg/median/max/std)', 
                 stream, len(data), mean(data), median(data), max(data),  
                 std(data))
  return stats

def compare_stats(reference, candidate):
  reason = []

  # Implement thresholds
  # 1. Install if there are differences between the sets in the files
  new_streams = set(candidate.keys()) ^ set(reference.keys())
  if new_streams:
    logging.info('Stream differences encountered: %r', new_streams)
    return 'Stream differences encountered: %r' % new_streams

  # 2. Check each stream.  
  for stream in reference:
    # 2.1 Install the candidate if candidate.median differs from
    # reference.mean by more than 0.675 * reference.std.  In a normal
    # distribution 50% of samples are within 0.675 sigma. For this to
    # hold true the median must be somewhere in the
    # -0.675s<median<0.675s range.  If the new median is outside this
    # range then it is pretty clear that the distribution is skewed
    # and a resort is needed.
    threshold = 0.675 * reference[stream].std()
    stream_variation = abs(median(candidate[stream])-
                           mean(reference[stream]))
    if stream_variation > threshold:
      reason.append(
        'Median interval for stream %s exceeds threshold: (%.03f/%.03f)' % (
          stream, stream_variation, threshold))

    # 2.2 Install the candidate if the max candidate gap is more than
    # twice the median reference gap.  This is mainly to catch if a
    # certain title is being read out of order.
    candidate_max = max(candidate[stream])
    threshold = 2 * median(reference[stream])
    if candidate_max > threshold:
      reason.append(
        'Maximum interval for stream %s exceeds twice median reference '
        'interval (%.03f/%.03f)' % (stream, candidate_max, threshold))

  [logging.info(r) for r in reason]
  return reason

def main():
  logging.info('Processing reference file (%r)', ARGS.reference)
  reference = stream_stats(ReadingList(ARGS.reference).list_issues())
  for candidate in ARGS.candidate:
    logging.info('Processing candidate file (%r)', candidate)
    candidate_streams = stream_stats(ReadingList(candidate).list_issues())
    install_candidate = compare_stats(reference, candidate_streams)
    if install_candidate:
      if not ARGS.quiet:
        for reason in install_candidate:
          print 'Threshold passed: %s' % install_candidate
      print 'OK'
      break

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
