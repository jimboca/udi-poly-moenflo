#!/usr/bin/env python3
"""
Moen Flo NodeServer for Polyglot v3.
Monitors Flo by Moen smart water shutoff devices via aioflo.
"""

import sys

from udi_interface import Interface, LOGGER

from nodes import VERSION, Controller


def main():
    try:
        polyglot = Interface([Controller])
        polyglot.start(VERSION)
        polyglot.updateProfile()
        Controller(polyglot, 'controller', 'controller', 'Moen Flo Controller')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info('Moen Flo NodeServer stopped')
        sys.exit(0)


if __name__ == '__main__':
    main()
