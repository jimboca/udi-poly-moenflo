"""Smoke tests for udi-poly-moenflo."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodes.FloDevice import FloDevice, _system_mode_index, _valve_index


class TestFloDeviceParsing(unittest.TestCase):
    def test_valve_index(self):
        self.assertEqual(_valve_index('open'), 1)
        self.assertEqual(_valve_index('closed'), 0)

    def test_system_mode_index(self):
        self.assertEqual(_system_mode_index('home'), 0)
        self.assertEqual(_system_mode_index('away'), 1)
        self.assertEqual(_system_mode_index('sleep'), 2)


if __name__ == '__main__':
    unittest.main()
