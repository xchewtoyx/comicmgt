#!/usr/bin/python
# Copyright 2013 Russell Heilling
import argparse

ARGS_PARSER = argparse.ArgumentParser()
ARGS = argparse.Namespace()

def add_argument(*args, **kwargs):
  ARGS_PARSER.add_argument(*args, **kwargs)

def parse_args(*args, **kwargs):
  ARGS_PARSER.parse_args(*args, namespace=ARGS, **kwargs)
