#!/usr/bin/python

import args
from calibredb import CalibreDB
import logs
from toread import ReadingList

ARGS = args.ARGS

args.add_argument('--todo_file', help='Location of todo.txt file',
                  default=os.path.join(os.environ['HOME'],
                                       'Dropbox/todo/todo.txt'))

def main():
  toread = ReadingList(ARGS.todo_file)
  for volumeid, volume_title in toread.list_volumes():
    print "%d: %s" % (volumeid, volume_title)


if __name__ == '__main__':
  args.parse_args()
  logs.set_logging()
  main()
