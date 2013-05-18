#!/usr/bin/python

import argparse

ARGS_PARSER = argparse.ArgumentParser()
ARGS = None

def add_argument(*args, **kwargs):
  ARGS_PARSER.add_argument(*args, **kwargs)

def parse_args(*args, **kwargs):
  ARGS = ARGS_PARSER.parse_args(*args, **kwargs)
  return ARGS
