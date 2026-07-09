"""Smoke tests for udi-poly-moenflo."""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nodes.FloDevice import (
    _current_hour_gallons,
    _minutes_since,
    _system_mode_index,
    _valve_index,
)


class TestFloDeviceParsing(unittest.TestCase):
    def test_valve_index(self):
        self.assertEqual(_valve_index('open'), 1)
        self.assertEqual(_valve_index('closed'), 0)

    def test_system_mode_index(self):
        self.assertEqual(_system_mode_index('home'), 0)
        self.assertEqual(_system_mode_index('away'), 1)
        self.assertEqual(_system_mode_index('sleep'), 2)

    def test_minutes_since(self):
        stamp = (datetime.now(timezone.utc) - timedelta(minutes=12)).strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        self.assertEqual(_minutes_since(stamp), 12)
        self.assertEqual(_minutes_since(None), 0)

    def test_current_hour_gallons(self):
        now = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
        earlier = now - timedelta(hours=1)
        consumption = {
            'aggregations': {'sumTotalGallonsConsumed': 5.5},
            'items': [
                {'time': earlier.isoformat(), 'gallonsConsumed': 1.1},
                {'time': now.isoformat(), 'gallonsConsumed': 2.25},
            ],
        }
        self.assertEqual(_current_hour_gallons(consumption), 2.25)
        self.assertEqual(_current_hour_gallons(None), 0.0)
        self.assertEqual(_current_hour_gallons({'items': []}), 0.0)


if __name__ == '__main__':
    unittest.main()
