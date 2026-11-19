import base64
import io
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


def lettering_frame(sign_height=91, sign_descent=2):
    atlas = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1920, 1536)
    ctx = cairo.Context(atlas)
    ctx.rectangle(12, 22, 94, 153)
    ctx.rectangle(10, 768 + 24, 113, 154)
    i = cluster.LABELS.index("%")
    ctx.rectangle(i % 6 * 320 + 8, i // 6 * 192 + 150 + sign_descent - sign_height, 96, sign_height)
    ctx.fill()
    png = io.BytesIO()
    atlas.write_to_png(png)
    widths = [[130] * len(cluster.LABELS) for _ in range(2)]
    widths[1][cluster.LABELS.index("km/h")] = 318  # Novum Medium in older car apps
    return {"version": 1, "labels": cluster.LABELS, "png": base64.b64encode(png.getvalue()),
            "advances": widths}


class InstrumentTests(unittest.TestCase):
    def test_speed_ink_on_wide_and_tall_screens(self):
        frame = lettering_frame()
        legacy = cluster.Lettering(frame)
        current = cluster.Lettering(dict(frame, speedRow=1))
        self.assertEqual(legacy.zero_ink, (94, 153, 1))
        self.assertEqual(current.zero_ink, (113, 154, 4))
        pair = cairo.ImageSurface(cairo.FORMAT_A8, 400, 350)
        ctx = cairo.Context(pair)
        ctx.translate(-754, 0)
        cluster.paint_speed(ctx, "00", 480, cluster.DAY[1], current)
        pair.flush()
        scan = bytes(pair.get_data())[220 * pair.get_stride():220 * pair.get_stride() + 400]
        starts = [x for x in range(1, 400) if scan[x - 1] < 128 <= scan[x]]
        self.assertEqual(len(starts), 2)
        self.assertAlmostEqual(starts[1] - starts[0], 0.34 * 480 * 0.72 * 1.14, delta=1)
        for lettering in (None, legacy, current):
            for width, height in ((1920, 480), (1920, 448), (1280, 720)):
                with self.subTest(lettering=lettering, size=(width, height)):
                    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
                    cluster.draw(cairo.Context(surface), width, height, {"speed_display_aaos": 0}, lettering)
                    surface.flush()
                    pixels = memoryview(surface.get_data()).cast("I")
                    face_height = min(height, width / 4)
                    center = height / 2
                    ink = [(x, y) for y in range(int(center - face_height / 4), int(center + face_height / 6))
                           for x in range(width * 2 // 5, width * 3 // 5) if pixels[y * width + x] & 255 < 154]
                    xs, ys = zip(*ink)
                    ink_height = max(ys) - min(ys) + 1
                    self.assertAlmostEqual(ink_height, 0.34 * face_height, delta=2)
                    self.assertAlmostEqual(max(xs) - min(xs) + 1, 0.72 * ink_height, delta=2)
                    self.assertAlmostEqual(max(ys) + 1, center + 0.148 * face_height, delta=2)

    def test_left_readings_and_percent_ink(self):
        for height, descent in ((91, 2), (114, 14)):  # Cap-height and legacy Novum percent signs
            face = cluster.Lettering(dict(lettering_frame(height, descent), speedRow=1))
            for dark in (False, True):
                with self.subTest(percent_height=height, dark=dark):
                    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 1920, 448)
                    fields = {"range_m_aaos": 0, "soc_aaos": 0, "usable_capacity_wh": 100}
                    cluster.draw(cairo.Context(surface), 1920, 448, fields, face, dark=dark)
                    surface.flush()
                    pixels = memoryview(surface.get_data()).cast("I")
                    bg = pixels[0] & 255

                    def ink_rows(left, right, top=225, bottom=280):
                        return [y for y in range(top, bottom) if any(
                            abs((pixels[y * 1920 + x] & 255) - bg) > 30 for x in range(left, right))]

                    self.assertAlmostEqual(len(ink_rows(192, 226, 145, 215)), 45, delta=1)
                    digit = ink_rows(261, 285)
                    sign = ink_rows(286, 326)
                    self.assertAlmostEqual(len(digit), 28, delta=1)
                    self.assertAlmostEqual(len(sign) / len(digit), 0.72, delta=0.06)
                    self.assertAlmostEqual(digit[-1], sign[-1], delta=1)
                    self.assertFalse(ink_rows(1338, 1510, 145, 280))

    def test_independent_units_and_reverse_speed(self):
        self.assertEqual(labels({"speed_display_aaos": -26.8224, "speed_unit": "mph",
                                 "range_m_aaos": 160934.4, "distance_unit": "km"}),
                         ["60", "mph", "161", "km"])
        self.assertEqual(labels({"range_m_aaos": 160934.4, "distance_unit": "mi"}), ["–", "100", "mi"])

    def test_usable_capacity_and_unknown_signals(self):
        self.assertEqual(labels({"soc_aaos": 45, "usable_capacity_wh": 50, "pack_capacity_wh": 100}), ["–", "90", "%"])
        self.assertEqual(labels({"soc_aaos": 45, "usable_capacity_wh": 0, "pack_capacity_wh": 100}), ["–", "45", "%"])
        self.assertEqual(labels({"soc_aaos": 110, "usable_capacity_wh": 100}), ["–", "100", "%"])
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
