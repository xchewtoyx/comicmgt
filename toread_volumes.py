#!/usr/bin/python

import args
from calibredb import CalibreDB
import logs
from toread import ReadingList

ARGS = args.ARGS

args.add_argument('--todo_file', help='Location of todo.txt file',
                  default=os.path.join(os.environ['HOME'],
                                       'Dropbox/todo/todo.txt'))
args.add_argument('--short', '-s', action='store_true',
                  help='Output simple comma separated list.')

def main():
  toread = ReadingList(ARGS.todo_file)
  volumes = list(toread.list_volumes())
  if ARGS.short:
    print ','.join([str(volumeid) for volumeid,title in volumes])
  else:
    for volumeid, volume_title in volumes:
      print "%d: %s" % (volumeid, volume_title)


if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
