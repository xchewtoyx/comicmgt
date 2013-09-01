# Copyright 2013 Russell Heilling
import logging
import sys

import args

args.add_argument('--verbose', '-v', action='count',
                  help='Enable verbose logging.')
ARGS = args.ARGS

LEVEL_SETTERS = set([logging.getLogger().setLevel])

def register_logger(level_setter):
  LEVEL_SETTERS.add(level_setter)

def set_logging():
  level = logging.WARN
  if ARGS.verbose > 1:
    level = logging.DEBUG
  if ARGS.verbose == 1:
    level = logging.INFO
  for setter in LEVEL_SETTERS:
    setter(level)

