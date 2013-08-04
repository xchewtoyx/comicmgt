#!/usr/bin/python
# Copyright 2013 Russell Heilling

import sys

import args
ARGS=None
args.add_argument('--rate', '-r', default='10', type=float,
                  help='Ratio of lines to take from the first vs second file')
args.add_argument('files', nargs=2, help='Files to merge')

def read_lines(filename, rate):
  with open(filename, 'r') as infile:
    lines = []
    collected = 0.0
    for line in infile:
      lines.append(line)
      collected += 1.0
      if collected >= rate:
        yield lines
	collected -= rate
        lines = []
    if lines:
      yield lines

def next_chunk(generator):
  try:
    return generator.next()
  except StopIteration:
    return []

def main():
  firstfile = read_lines(ARGS.files[0], ARGS.rate)
  secondfile = read_lines(ARGS.files[1], 1)
  while True:
    lines = []
    lines.extend(next_chunk(firstfile))
    lines.extend(next_chunk(secondfile))
    if len(lines) == 0:
      break
    sys.stdout.writelines(lines)

if __name__ == '__main__':
  ARGS=args.parse_args()
  main()
