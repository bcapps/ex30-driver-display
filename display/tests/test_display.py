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
    i = len(cluster.READINGS)
    ctx.rectangle(i % 6 * 320 + 10, i // 6 * 192 + 24, 113, 154)
    i = cluster.READINGS.index("%")
    ctx.rectangle(i % 6 * 320 + 8, i // 6 * 192 + 150 + sign_descent - sign_height, 96, sign_height)
    ctx.fill()
    png = io.BytesIO()
    atlas.write_to_png(png)
    advances = [130] * (len(cluster.READINGS) + len(cluster.DIGITS_AND_GEARS))
    advances.extend(100 + i for i in range(len(cluster.CAPTIONS)))
    return {"type": "lettering", "version": 4, "png": base64.b64encode(png.getvalue()).decode(),
            "advances": advances}


class InstrumentTests(unittest.TestCase):
    def test_speed_ink_on_wide_and_tall_screens(self):
        face = cluster.Lettering(lettering_frame())
        self.assertEqual(face.zero_ink, (113, 154, 4))
        pair = cairo.ImageSurface(cairo.FORMAT_A8, 400, 350)
        ctx = cairo.Context(pair)
        ctx.translate(-754, 0)
        cluster.paint_speed(ctx, "00", 480, cluster.DAY[1], face)
        pair.flush()
        scan = bytes(pair.get_data())[220 * pair.get_stride():220 * pair.get_stride() + 400]
        starts = [x for x in range(1, 400) if scan[x - 1] < 128 <= scan[x]]
        self.assertEqual(len(starts), 2)
        self.assertAlmostEqual(starts[1] - starts[0], 0.34 * 480 * 0.72 * 1.14, delta=1)
        for lettering in (None, face):
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
        for height, descent in ((91, 2), (114, 14)):  # Font metrics vary with the typeface installed in the car.
            face = cluster.Lettering(lettering_frame(height, descent))
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

    def test_ready_aligns_with_range_only_during_a_reported_departure(self):
        fields = {"speed_display_aaos": 0, "soc_aaos": 90, "usable_capacity_wh": 100, "range_m_aaos": 305000}
        for dark in (False, True):
            for gear in ("P", "N", "D", "R"):
                for cue in (None, "welcome", "ready"):
                    with self.subTest(dark=dark, gear=gear, cue=cue), patch("cluster.paint_text", wraps=cluster.paint_text) as text:
                        cluster.draw(canvas(), 960, 240, dict(fields, gear_selected=gear, start_cue=cue), dark=dark)
                        calls = {call.args[1]: call.args for call in text.call_args_list}
                        expected = cue == "ready" and gear in ("D", "R")
                        self.assertEqual("READY" in calls, expected)
                        if expected:
                            _, _, x, y, size, color, _ = calls["READY"]
                            self.assertEqual(x, calls["305"][2])
                            self.assertGreater(y - size, calls["%"][3])
                            self.assertLess(size, calls["90"][4])
                            self.assertGreater(int(color[3:5], 16), max(int(color[1:3], 16), int(color[5:], 16)))

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

    def test_parking_brake_does_not_join_the_previous_text_path(self):
        fields = {"gear_selected": "P", "speed_display_aaos": 0, "soc_aaos": 64, "usable_capacity_wh": 100}
        for welcome in (False, True):
            rows = []
            for engaged in (False, True):
                ctx = canvas()
                cluster.draw(ctx, 960, 240, dict(fields, start_cue="welcome" if welcome else None, parking_brake=engaged))
                surface = ctx.get_target()
                surface.flush()
                stride = surface.get_stride()
                rows.append(bytes(surface.get_data()[80 * stride:81 * stride]))
            with self.subTest(welcome=welcome):
                self.assertTrue(rows[0] == rows[1], "A stroke from the parking brake crossed the display")

    def test_charging_from_vehicle_state_or_parked_power_reading(self):
        plugged = {"charge_port_connected": True, "gear_selected": "P", "speed_display_aaos": 0}
        self.assertEqual(cluster.display_mode(plugged), "plugged")
        self.assertEqual(cluster.display_mode(dict(plugged, battery_power_mw=4_000)), "plugged")
        self.assertEqual(cluster.display_mode(dict(plugged, battery_power_mw=1_400_000)), "charging")
        self.assertEqual(cluster.display_mode({"charge_state": "charging"}), "charging")
        self.assertEqual(cluster.display_mode({"battery_power_mw": 22_000_000}), "driving")
        self.assertEqual(cluster.display_mode({"charge_state": "idle", "gear_selected": "P"}), "driving")
        for state, mode in (("idle", "plugged"), ("charging", "charging"), ("full", "full"), ("fault", "fault")):
            fields = dict(plugged, charge_state=state, battery_power_mw=22_000_000)
            self.assertEqual(cluster.display_mode(fields), mode)
            for change in ({"charge_port_connected": False}, {"gear_selected": "D"}, {"gear_selected": "R"},
                           {"gear_selected": "N"}, {"speed_display_aaos": -0.5}):
                with self.subTest(state=state, change=change):
                    self.assertEqual(cluster.display_mode(dict(fields, **change)), "driving")

    def test_welcome_requires_confirmed_stationary_park_before_driving(self):
        parked = {"start_cue": "welcome", "gear_selected": "P", "speed_display_aaos": 0}
        self.assertEqual(cluster.display_mode(parked), "welcome")
        for changes in ({"start_cue": None}, {"gear_selected": "D"}, {"gear_selected": "R"},
                        {"gear_selected": "N"}, {"gear_selected": "UNKNOWN"}, {"speed_display_aaos": -0.1},
                        {"speed_display_aaos": None}):
            with self.subTest(changes=changes):
                self.assertEqual(cluster.display_mode(dict(parked, **changes)), "driving")
        self.assertEqual(cluster.display_mode({"gear_selected": "P", "speed_display_aaos": 0}), "driving")
        self.assertEqual(cluster.display_mode(dict(parked, charge_state="charging")), "charging")
        self.assertEqual(cluster.display_mode(dict(parked, charge_port_connected=True)), "plugged")
        self.assertEqual(labels(parked), list(cluster.WELCOME_LABELS))
        self.assertEqual(labels(dict(parked, soc_aaos=64, usable_capacity_wh=100,
                                     range_m_aaos=160934.4, distance_unit="mi")),
                         [*cluster.WELCOME_LABELS, "100", "mi", "64", "%"])

    @patch("cluster.time.monotonic")
    def test_welcome_entrance_and_interrupted_handoff(self, clock):
        parked = {"start_cue": "welcome", "gear_selected": "P", "speed_display_aaos": 0}
        moving = dict(parked, gear_selected="R", speed_display_aaos=-5)
        transition = cluster.FaceTransition()

        def frame(now, fields):
            clock.return_value = now
            with patch("cluster.paint_text", wraps=cluster.paint_text) as text:
                animating = cluster.draw(canvas(), 960, 240, fields, transition=transition)
            return animating, [call.args[1] for call in text.call_args_list]

        self.assertEqual(frame(1, parked), (True, []))
        self.assertEqual(frame(1.12, parked), (True, list(cluster.WELCOME_LABELS)))
        self.assertEqual(frame(2, parked), (False, list(cluster.WELCOME_LABELS)))
        self.assertTrue(frame(3, moving)[0])
        self.assertFalse(frame(4, moving)[0])
        transition.progress(None)  # Lost the connection while driving.
        self.assertFalse(frame(5, moving)[0])
        frame(6, parked)
        self.assertNotIn("Hello", frame(6, moving)[1])  # Shift before the greeting ever became visible.

    @patch("cluster.time.monotonic")
    def test_whole_welcome_crossfades_over_the_live_driving_face(self, clock):
        parked = {"start_cue": "welcome", "gear_selected": "P", "speed_display_aaos": 0,
                  "range_m_aaos": 128_000, "soc_aaos": 31, "usable_capacity_wh": 100}
        selected = dict(parked, gear_selected="D", range_m_aaos=127_000)
        moving = dict(selected, speed_display_aaos=5, battery_power_mw=-12_000_000)

        def render(fields, transition=None):
            ctx = canvas()
            cluster.draw(ctx, 960, 240, fields, dark=dark, transition=transition)
            return ctx.get_target()

        def pixels(surface):
            surface.flush()
            return bytes(surface.get_data())

        for dark in (False, True):
            with self.subTest(dark=dark):
                transition = cluster.FaceTransition()
                clock.return_value = 0
                render(parked, transition)
                welcome = render(parked)
                clock.return_value = 1
                self.assertTrue(pixels(render(selected, transition)) == pixels(welcome))

                clock.return_value = 1.16
                actual = pixels(render(moving, transition))
                expected = render(moving)
                ctx = cairo.Context(expected)
                # Half of the 4 px exit motion is one device pixel on this half-size canvas.
                ctx.set_source_surface(welcome, 0, 1)
                ctx.paint_with_alpha(0.5)
                self.assertTrue(all(abs(a - b) <= 1 for a, b in zip(actual, pixels(expected))),
                                "Every instrument should follow the same dissolve")

                clock.return_value = 1.33
                self.assertTrue(pixels(render(moving, transition)) == pixels(render(moving)))
                clock.return_value = 2
                render(parked, transition)
                clock.return_value = 2.08
                partial_welcome = pixels(render(parked, transition))
                self.assertTrue(pixels(render(moving, transition)) == partial_welcome)

    def test_complete_lettering_includes_every_caption(self):
        frame = lettering_frame()
        stream = Stream()
        stream.feed(json.dumps(frame).encode() + b"\n")
        for i, (label, em) in enumerate(cluster.CAPTIONS):
            with self.subTest(label=label):
                self.assertEqual(cluster.text_width(canvas(), label, em, stream.lettering), 100 + i)
        for widths in (frame["advances"][:-1], [float("nan")] * len(frame["advances"])):
            with self.assertRaises(ValueError):
                cluster.Lettering(dict(frame, advances=widths))

    def test_charging_uses_only_available_readings(self):
        fields = {"charge_state": "charging", "soc_aaos": 32_000, "usable_capacity_wh": 50_000,
                  "range_m_aaos": 160934.4, "distance_unit": "mi", "battery_power_mw": 7_200_000,
                  "charge_target_pct": 90, "charge_seconds_remaining": 4450}
        self.assertEqual(labels(fields), ["Charging", "100", "mi", "Done in", "1", "h", "15", "min",
                                           "7.2", "kW", "64", "%", "90", "%"])
        self.assertEqual(labels({"charge_state": "charging", "battery_power_mw": -1_000_000,
                                 "charge_target_pct": 150, "charge_seconds_remaining": 0}), ["Charging", "–"])
        self.assertEqual(list(cluster.charging_details({"charge_seconds_remaining": 3600}, "charging")), [["Done in", "1", "h"]])
        self.assertEqual(list(cluster.charging_details({"charge_seconds_remaining": 1}, "charging")), [["Done in", "1", "min"]])

    def test_parked_charge_labels_and_fixed_fill(self):
        fields = dict(charge_port_connected=True, charge_target_pct=80, soc_aaos=80, usable_capacity_wh=100,
                      charge_seconds_remaining=70, battery_power_mw=7_000_000)
        for state, title in (("idle", "Plugged in"), ("full", "Target reached"), ("fault", "Charging fault")):
            sample = dict(fields, charge_state=state)
            self.assertEqual(labels(sample), [title, "80", "%", "80", "%"])
            for dark in (True, False):
                def render(now):
                    ctx = canvas()
                    with patch("cluster.time.monotonic", return_value=now):
                        cluster.draw(ctx, 960, 240, sample, dark=dark)
                    return bytes(ctx.get_target().get_data())
                self.assertTrue(render(0) == render(2))
        self.assertEqual(labels({"charge_state": "fault"}), ["Charging fault", "–"])

    def test_battery_warning_bands_and_vehicle_flag(self):
        for dark in (False, True):
            colors = [cluster.battery_ink(p, False, dark) for p in (16, 15, 10, 5)]
            self.assertEqual(len(set(colors)), 4)
            self.assertEqual(cluster.battery_ink(80, True, dark), colors[1])
            self.assertEqual(cluster.battery_ink(5, True, dark), colors[3])
            self.assertEqual(cluster.battery_ink(0, False, dark), colors[3])
        self.assertEqual(labels({"battery_low": True}), ["–", "–"])

    def test_snowflake_follows_pack_temperature_on_each_face(self):
        faces = (
            {"gear_selected": "D"},
            {"start_cue": "welcome", "gear_selected": "P", "speed_display_aaos": 0},
            {"charge_port_connected": True},
            {"charge_state": "charging"},
            {"charge_state": "full"},
            {"charge_state": "fault"},
        )
        for face in faces:
            for pack, visible in ((-0.1, True), (0, False), (8, False), (None, False), (float("nan"), False)):
                fields = dict(face, soc_aaos=45, usable_capacity_wh=100)
                if pack is not None:
                    fields["pack_temp_c"] = pack
                with self.subTest(face=face, pack=pack), patch("cluster.snowflake") as flake:
                    cluster.draw(canvas(), 960, 240, fields)
                    self.assertEqual(flake.call_count, int(visible))

    @patch("cluster.time.monotonic", lambda: 0)
    def test_solid_charging_band_and_limit_use_one_scale(self):
        for width, height in ((1920, 480), (1920, 448), (1280, 720)):
            face = min(height, width / 4)
            top = round(height / 2 - 0.29 * face)
            bottom = round(height / 2 + 0.32 * face)
            for dark in (False, True):
                for charge, limit in ((64, 90), (90, 90), (75, 50), (100, 100)):
                    with self.subTest(size=(width, height), dark=dark, charge=charge, limit=limit):
                        fields = {"charge_state": "charging", "usable_capacity_wh": 100,
                                  "soc_aaos": charge, "charge_target_pct": limit}
                        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
                        cluster.draw(cairo.Context(surface), width, height, fields, dark=dark)
                        surface.flush()
                        pixels = memoryview(surface.get_data()).cast("I")

                        def pixel(x, y):
                            return pixels[y * width + x] & 0xffffff

                        bg = pixel(0, 0)
                        green = 0x2b7e49 if dark else 0x3aaa62
                        end = int(1808 / 1920 * width * charge / 100)
                        marker = int(1808 / 1920 * width * limit / 100)
                        for y in (top + 2, bottom - 4):
                            self.assertEqual(pixel(0, y), green)
                            self.assertEqual(pixel(end - 5, y), green)
                        self.assertEqual(pixel(end - 1, top + 2), green)
                        self.assertEqual(pixel(end + 1, top + 2), bg)
                        self.assertEqual(pixel(0, top - 2), bg)
                        self.assertEqual(pixel(0, bottom + 1), bg)
                        self.assertEqual(pixel(marker, bottom - 4), 0xffffff if dark else 0x2e2e2e)
                        self.assertEqual(pixel(marker, bottom + 1), bg)

    @patch("cluster.time.monotonic", lambda: 0)
    def test_changing_limit_only_moves_the_marker_and_its_label(self):
        def above_marker(charge, limit):
            ctx = canvas()
            fields = {"charge_state": "charging", "soc_aaos": charge, "usable_capacity_wh": 100,
                      "range_m_aaos": 384_000, "battery_power_mw": 22_000_000,
                      "charge_seconds_remaining": 4500, "charge_target_pct": limit}
            cluster.draw(ctx, 960, 240, fields)
            surface = ctx.get_target()
            surface.flush()
            # At this size the limit marker starts on row 176.
            return bytes(surface.get_data()[:176 * surface.get_stride()])

        for charge in (64, None):
            reference = above_marker(charge, 90)
            for limit in (0, 50, 100, None):
                with self.subTest(charge=charge, limit=limit):
                    self.assertTrue(above_marker(charge, limit) == reference,
                                    "Changing the charge limit altered the display above the marker")

    def test_charging_percent_and_limit_label_placement(self):
        for sign_height, descent in ((91, 2), (114, 14)):
            face = cluster.Lettering(lettering_frame(sign_height, descent))
            for limit in (0, 50, 90, 100):
                with self.subTest(sign_height=sign_height, limit=limit):
                    fields = {"charge_state": "charging", "soc_aaos": 0, "usable_capacity_wh": 100,
                              "charge_target_pct": limit}
                    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 1920, 480)
                    cluster.draw(cairo.Context(surface), 1920, 480, fields, face)
                    surface.flush()
                    pixels = memoryview(surface.get_data()).cast("I")
                    marker = round(1808 * limit / 100)

                    def ink(left, right, top, bottom):
                        return [(x, y) for y in range(top, bottom) for x in range(left, right)
                                if pixels[y * 1920 + x] & 255 < 128]

                    if limit == 0:
                        self.assertTrue(ink(12, 100, 350, 395))
                        continue

                    # The current reading keeps its place from the original 90% layout.
                    digit = [y for _, y in ink(1427, 1563, 130, 290)]
                    sign = [y for _, y in ink(1563, 1627, 130, 290)]
                    self.assertAlmostEqual((max(sign) - min(sign)) / (max(digit) - min(digit)), 0.25, delta=0.02)
                    self.assertAlmostEqual(max(sign), max(digit), delta=1)
                    self.assertFalse(ink(1627, 1707, 130, 290))
                    self.assertFalse(ink(marker + 2, marker + 100, 350, 395))
                    xs, ys = zip(*ink(marker - 112, marker - 2, 350, 395))
                    self.assertLessEqual(max(xs), marker - 10)
                    self.assertAlmostEqual((min(ys) + max(ys)) / 2, 373.5, delta=2)


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
        frame = lettering_frame()
        for malformed in (dict(frame, version=3), dict(frame, png="AAAA")):
            with self.assertRaises(ValueError):
                Stream().feed(json.dumps(malformed).encode() + b"\n")
