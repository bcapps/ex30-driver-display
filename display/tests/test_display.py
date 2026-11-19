import json
import unittest
from unittest.mock import patch

import cairo
import cluster
from stream import MAX_LINE, Stream


def canvas():
    return cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 960, 240))


def labels(fields):
    with patch("cluster.paint_text", wraps=cluster.paint_text) as text:
        cluster.draw(canvas(), 960, 240, fields)
    return [call.args[1] for call in text.call_args_list]


class InstrumentTests(unittest.TestCase):
    def test_independent_units_and_reverse_speed(self):
        self.assertEqual(labels({"speed_display_aaos": -26.8224, "speed_unit": "mph",
                                 "range_m_aaos": 160934.4, "distance_unit": "km"}),
                         ["60", "mph", "161", "km"])
        self.assertEqual(labels({"range_m_aaos": 160934.4, "distance_unit": "mi"}), ["–", "100", "mi"])

    def test_usable_capacity_and_unknown_signals(self):
        self.assertEqual(labels({"soc_aaos": 45, "usable_capacity_wh": 50, "pack_capacity_wh": 100}), ["–", "90%"])
        self.assertEqual(labels({"soc_aaos": 45, "usable_capacity_wh": 0, "pack_capacity_wh": 100}), ["–", "45%"])
        self.assertEqual(labels({"soc_aaos": 45, "gear_selected": "UNKNOWN", "speed_display_aaos": float("nan")}), ["–"])
        self.assertEqual(labels({"speed_display_aaos": 0}), ["0", "km/h"])

    def test_parking_brake_independent_of_selected_gear(self):
        with patch("cluster.parking_brake") as brake:
            cluster.draw(canvas(), 960, 240, {"gear_selected": "P"})
            brake.assert_not_called()
            cluster.draw(canvas(), 960, 240, {"parking_brake": True})
            brake.assert_called_once()


class StreamTests(unittest.TestCase):
    @patch("stream.Lettering")
    def test_partial_line_full_replacement_and_stale_reset(self, lettering):
        stream = Stream()
        frames = [{"type": "lettering"},
                  {"type": "state", "fields": {"night_mode": False, "speed_display_aaos": 20}},
                  {"type": "state", "fields": {"night_mode": False}}]
        data = b"".join(json.dumps(f).encode() + b"\n" for f in frames)
        with patch("stream.time.monotonic", return_value=100):
            for i in range(0, len(data), 7):
                stream.feed(data[i:i + 7])
        self.assertTrue(stream.live)
        self.assertEqual(stream.fields, {"night_mode": False})
        self.assertEqual(stream.deadline, 103)
        stream.reset()
        self.assertFalse(stream.live)
        self.assertFalse(stream.dark)
        self.assertIsNone(stream.lettering)
        self.assertEqual(stream.fields, {})
        lettering.assert_called_once()

    def test_reject_invalid_frames(self):
        for wire in (b'{"type":"state","fields":{}}\n', b"[]\n", b"invalid\n", b"X" * (MAX_LINE + 1)):
            with self.subTest(wire=wire[:20]), self.assertRaises(ValueError):
                Stream().feed(wire)

    def test_reject_unexpected_lettering(self):
        with self.assertRaises(ValueError):
            cluster.Lettering({"version": 1, "labels": cluster.LABELS, "png": "AAAA"})
