import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import shiftly


class ValidationTest(unittest.TestCase):
    def test_accepts_normal_phase(self):
        self.assertEqual(shiftly.validate_phase("  Sit ", "40"), ("Sit", 40.0))

    def test_rejects_bad_minutes(self):
        for bad in ("nan", "inf", "-inf", "0", "-5", "abc", "", None, True, "1e9", "0.01"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                shiftly.validate_phase("Sit", bad)

    def test_rejects_bad_names(self):
        for bad in ("", "   ", "x" * 41, "a\nb", "a\x00b"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                shiftly.validate_phase(bad, 10)

    def test_config_rejects_duplicates_empty_and_too_many(self):
        with self.assertRaises(ValueError):
            shiftly.validate_config([("A", 1), ("a", 2)], True, True)
        with self.assertRaises(ValueError):
            shiftly.validate_config([], True, True)
        with self.assertRaises(ValueError):
            shiftly.validate_config([(f"p{i}", 1) for i in range(51)], True, True)


class LoadConfigTest(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config.json")
            with open(path, "w") as f:
                f.write(text)
            old, shiftly.CONFIG_PATH = shiftly.CONFIG_PATH, path
            try:
                return shiftly.load_config()
            finally:
                shiftly.CONFIG_PATH = old

    def test_garbage_falls_back_to_defaults(self):
        for text in ("", "not json", "[]", "null", '{"phases": 5}', '{"phases": []}',
                     '{"phases": [{"name": "A", "minutes": NaN}]}'):
            self.assertEqual(self.load(text), shiftly.DEFAULT_CONFIG, msg=text)

    def test_drops_only_broken_phases(self):
        cfg = self.load(json.dumps({"phases": [
            {"name": "Sit", "minutes": 30},
            {"name": "", "minutes": 5},
            {"name": "Sit", "minutes": 9},
            {"minutes": 5},
            {"name": "Stand", "minutes": "x"},
            {"name": "Walk", "minutes": 2},
        ]}))
        self.assertEqual([p["name"] for p in cfg["phases"]], ["Sit", "Walk"])


class CycleTest(unittest.TestCase):
    def cycle(self, pause_on_lock=True):
        cfg = shiftly.validate_config([("Sit", 1), ("Stand", 2)], False, pause_on_lock)
        return shiftly.Cycle(cfg)

    def test_phase_rollover(self):
        c = self.cycle()
        self.assertFalse(c.tick(59))
        self.assertTrue(c.tick(1))
        self.assertEqual(c.phase["name"], "Stand")

    def test_pause_and_lock(self):
        c = self.cycle()
        c.locked = True
        self.assertFalse(c.tick(3600))
        self.assertEqual(c.remaining, 60)
        c.locked = False
        c.paused = True
        self.assertFalse(c.tick(3600))
        self.assertEqual(c.remaining, 60)

    def test_lock_ignored_when_option_off(self):
        c = self.cycle(pause_on_lock=False)
        c.locked = True
        self.assertTrue(c.tick(60))


if __name__ == "__main__":
    unittest.main()
