#!/usr/bin/python
# Copyright 2013 Russell Heilling
# pylint: disable=C0103
'''Sort a toread list against publication dates from the calibre database.'''
import logging
import subprocess
import sys

import args
from streams import StreamClassifier
import calibredb
import logs

args.add_argument('--archive', '-a', help='Archive file before sorting',
                  action='store_true')
args.add_argument('--todobin', '-t', help='path to todo.txt script',
                  type=str, default='todo.sh')
args.add_argument('--infile', '-i', help='path to input file',
                  default=sys.stdin)
args.add_argument('--outfile', '-o', help='path to output file',
                  default=sys.stdout)
ARGS = args.ARGS

def archive():
  'Archive todo list.'
  if ARGS.archive:
    try:
      output = subprocess.check_output([ARGS.todobin, 'archive'])
    except subprocess.CalledProcessError as error:
      logging.error('Unable to archive old items: %s', error.output)
    logging.info('Archive successful: %s', output)


def main():
  'Setup environment and run classification.'
  classifier = StreamClassifier()
  classifier.add_streams(catchup_streams=ARGS.catchup_stream, 
                         publisher_streams=ARGS.publisher)

  # Open input and sort by pubdate then name
  infile = ARGS.infile
  if isinstance(infile, basestring):
    infile = open(infile, 'r')
  for line in infile:
    classifier.identify(line)
  if infile is not sys.stdin:
    infile.close()
    
  # Write out sorted list
  outfile = ARGS.outfile
  if isinstance(outfile, basestring):
    outfile = open(outfile, 'w')
  for line in classifier.merged_streams():
    outfile.write(line + '\n')
  if outfile is sys.stdout:
    outfile.flush()
  else:
    outfile.close()

if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  try:
    main()
  except KeyboardInterrupt:
    sys.exit(1)
