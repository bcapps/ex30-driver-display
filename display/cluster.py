"""The Calm instrument face. All coordinates refer to its 1920 × 448 design."""
import base64
import io
import math
import struct
import time

import cairo

WIDTH, HEIGHT = 1920, 448
FADE_OFFSET = 4
# In the EX90 artwork, a 64% charge fills about 61% of the panel width.
CHARGE_TRACK_WIDTH = WIDTH - 112
# Sampled from Volvo's light and dark EX30 Calm reference images.
DAY = ("#f0f0f0", "#444444", "#969696", "#d6d6d6", "#c52631", "#22764c")
NIGHT = ("#2f3744", "#ffffff", "#99a5b3", "#717986", "#ff545b", "#69d99b")
LABELS = tuple("0123456789PRND") + ("km/h", "mph", "m/s", "mi", "km", "m", "%", "–")
CHARGING_LABELS = ("Charging", "Done in", "h", "min", "kW", ".")
WELCOME_LABELS = ("Hello", "Press the brake and select D or R to start")
CHARGE_TITLES = {"charging": "Charging", "plugged": "Plugged in", "full": "Target reached", "fault": "Charging fault"}
STATUS_LABELS = ("Plugged in", "Target reached", "Charging fault", "°C", "°F", "−")


def number(fields, key):
    value = fields.get(key)
    if type(value) in (int, float) and -3.403e38 <= value <= 3.403e38:
        return value
    return None


def whole(value):
    return str(math.floor(value + 0.5))


def set_color(ctx, color, alpha=1):
    ctx.set_source_rgba(*(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)), alpha)


def lettering_image(encoded, width, height):
    png = base64.b64decode(encoded, validate=True)
    if png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR" or png[16:24] != struct.pack(">II", width, height):
        raise ValueError("Unexpected lettering image size")
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


class Lettering:
    """Monochrome text painted by Android. No font software is sent to the Pi."""
    def __init__(self, frame):
        if frame.get("version") != 1 or tuple(frame["labels"]) != LABELS:
            raise ValueError("Unsupported lettering")
        self.surface = lettering_image(frame["png"], 1920, 1536)
        widths = frame["advances"]
        if (len(widths) != 2 or any(len(row) != len(LABELS) for row in widths)
                or any(type(w) not in (int, float) or not 0 < w <= 320 for row in widths for w in row)):
            raise ValueError("Invalid label widths")
        self.widths = widths
        self.status_widths = frame.get("statusAdvances")
        if self.status_widths is not None:
            if (len(self.status_widths) != len(STATUS_LABELS) or
                    any(type(w) not in (int, float) or not 0 < w <= 508 for w in self.status_widths)):
                raise ValueError("Invalid status label widths")
            self.status_surface = lettering_image(frame["statusPng"], 1536, 192)
        self.charging_widths = frame.get("chargingAdvances")
        if self.charging_widths is not None and (len(self.charging_widths) != len(CHARGING_LABELS) or
                any(type(w) not in (int, float) or not 0 < w <= 316 for w in self.charging_widths)):
            raise ValueError("Invalid charging label widths")
        self.welcome_widths = frame.get("welcomeAdvances")
        if self.welcome_widths is not None and (len(self.welcome_widths) != len(WELCOME_LABELS) or
                any(type(w) not in (int, float) or not 0 < w <= 636 for w in self.welcome_widths)):
            raise ValueError("Invalid welcome label widths")
        self.speed_row = frame.get("speedRow", 0)
        if type(self.speed_row) is not int or self.speed_row not in (0, 1):
            raise ValueError("Invalid speed lettering row")
        self.zero_ink = self.measure_ink("0", self.speed_row)
        _, digit_height, digit_bottom = self.zero_ink if self.speed_row == 0 else self.measure_ink("0", 0)
        _, sign_height, sign_bottom = self.measure_ink("%", 0)
        self.digit_ink = (digit_height / 216, digit_bottom / 216)
        self.percent_ink = (sign_height / 128, sign_bottom / 128)

    def measure_ink(self, label, block):
        index = LABELS.index(label)
        tile = cairo.ImageSurface(cairo.FORMAT_A8, 320, 192)
        ctx = cairo.Context(tile)
        ctx.set_source_surface(self.surface, -(index % 6) * 320, -block * 768 - index // 6 * 192)
        ctx.paint()
        tile.flush()
        mask = bytes(tile.get_data()).translate(bytes(128) + b"\xff" * 128)
        rows = [mask[y:y + 320] for y in range(0, len(mask), tile.get_stride())]
        ink = [(y, row.find(b"\xff"), row.rfind(b"\xff")) for y, row in enumerate(rows) if b"\xff" in row]
        if not ink:
            raise ValueError(f"Missing lettering for {label}")
        left = min(left for _, left, _ in ink)
        right = max(right for _, _, right in ink) + 1
        bottom = ink[-1][0] + 1
        baseline = 174 if index < 10 else 150
        return right - left, bottom - ink[0][0], bottom - baseline

    def layout(self, text, size, weight):
        if self.welcome_widths and text in WELCOME_LABELS:
            i = WELCOME_LABELS.index(text)
            top, baseline, height, em = ((1440, 67, 69, 88), (1509, 25, 27, 32))[i]
            scale = size / em
            return [(self.surface, 1280, top, 640, baseline, height, scale, self.welcome_widths[i] * scale)]
        labels = (text,) if text in LABELS or text in CHARGING_LABELS or text in STATUS_LABELS else text
        glyphs = []
        for label in labels:
            if label in LABELS:
                i = LABELS.index(label)
                left, top = i % 6 * 320, weight * 768 + i // 6 * 192
                baseline, height = (174 if i < 10 else 150), 192
                scale = size / (216 if i < 10 else 128)
                advance = self.widths[weight][i] * scale
            elif self.charging_widths and label in CHARGING_LABELS:
                i = CHARGING_LABELS.index(label)
                left, top = (4 + i % 2) * 320, i // 4 * 768 + 576 + i // 2 % 2 * 96
                baseline, height, scale = 74, 96, size / 72
                advance = self.charging_widths[i] * scale
            elif self.status_widths and label in STATUS_LABELS:
                i = STATUS_LABELS.index(label)
                scale = size / 64
                glyphs.append((self.status_surface, i % 3 * 512, i // 3 * 96, 512, 72, 96,
                               scale, self.status_widths[i] * scale))
                continue
            else:
                return None
            glyphs.append((self.surface, left, top, 320, baseline, height, scale, advance))
        return glyphs

    def draw(self, ctx, text, x, y, size, weight, align, tracking=0):
        glyphs = self.layout(text, size, weight)
        if glyphs is None:
            return None
        width = sum(g[-1] for g in glyphs) + tracking * (len(glyphs) - 1)
        ctx.save()
        ctx.translate(x - width * align, y)
        for surface, left, top, tile_width, baseline, height, scale, advance in glyphs:
            ctx.save()
            ctx.scale(scale, scale)
            ctx.rectangle(-4, -baseline, tile_width, height)
            ctx.clip()
            ctx.mask_surface(surface, -4 - left, -baseline - top)
            ctx.restore()
            ctx.translate(advance + tracking, 0)
        ctx.restore()
        return width


def text_width(ctx, text, size, lettering=None, weight=0):
    if lettering is not None:
        glyphs = lettering.layout(text, size, weight)
        if glyphs is not None:
            return sum(g[-1] for g in glyphs)
    ctx.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if weight else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    return ctx.text_extents(text)[4]


def paint_text(ctx, text, x, y, size, color, lettering=None, weight=0, align=0):
    set_color(ctx, color)
    if lettering is not None:
        width = lettering.draw(ctx, text, x, y, size, weight, align)
        if width is not None:
            return width
    # Desktop previews, setup messages and words missing from an older car app.
    width = text_width(ctx, text, size, weight=weight)
    ctx.move_to(x - width * align, y)
    ctx.show_text(text)
    return width


def paint_speed(ctx, text, face_height, ink, lettering):
    ctx.save()
    if lettering is None:
        ctx.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(216)
        _, top, width, height, _, _ = ctx.text_extents("0")
        descent = top + height
    else:
        width, height, descent = lettering.zero_ink
    # EX90 Calm supplies the size and placement. The EX30 strip's zero is
    # 100 by 139 pixels, with 12 pixels of clear space after the preceding 8.
    ink_height = 0.34 * face_height
    ctx.translate(954, HEIGHT / 2 + 0.148 * face_height)
    ctx.scale(0.72 * ink_height / width, ink_height / height)
    if lettering is None:
        paint_text(ctx, text, 0, -descent, 216, ink, align=0.5)
    else:
        set_color(ctx, ink)
        row = lettering.speed_row
        # The centres of the 8 and 0 are 114 pixels apart for a 100-pixel-wide zero.
        tracking = 1.14 * width - lettering.widths[row][0]
        lettering.draw(ctx, text, 0, -descent, 216, row, 0.5, tracking=tracking)
    ctx.restore()


def battery(ctx, x, y, percent, ink):
    set_color(ctx, ink)
    ctx.set_line_width(2.75)
    ctx.rectangle(x, y, 50, 24)
    ctx.stroke()
    ctx.rectangle(x + 52, y + 7, 3, 10)
    if percent is not None:
        ctx.rectangle(x + 3, y + 3, 44 * percent / 100, 18)
    ctx.fill()


def battery_ink(percent, low, dark):
    level = math.floor(percent + 0.5) if percent is not None else 100
    if level <= 5:
        return NIGHT[4] if dark else DAY[4]
    if level <= 10:
        return "#ff9956" if dark else "#ac5017"
    if level <= 15 or low is True:
        return "#ffbd53" if dark else "#936300"
    return NIGHT[1] if dark else DAY[1]


def snowflake(ctx, x, y, radius, color):
    # Six spokes, each with a single fork, like the EX30 temperature glyph.
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(radius, radius)
    set_color(ctx, color)
    ctx.set_line_width(0.12)
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    ctx.new_path()
    for _ in range(6):
        ctx.move_to(0, 0)
        ctx.line_to(0, -1)
        ctx.move_to(-0.24, -0.76)
        ctx.line_to(0, -0.52)
        ctx.line_to(0.24, -0.76)
        ctx.rotate(math.tau / 6)
    ctx.stroke()
    ctx.restore()


def cold_pack(fields):
    celsius = number(fields, "pack_temp_c")
    return celsius is not None and celsius < 0


def paint_outside_temperature(ctx, fields, lettering, dark):
    celsius = number(fields, "outside_temp_c")
    if celsius is None:
        return
    fahrenheit = fields.get("temperature_unit") == "F"
    degrees = math.floor(celsius * 9 / 5 + 32 if fahrenheit else celsius)
    color = NIGHT[2] if dark else "#686868"
    x = 82
    x += paint_text(ctx, str(degrees).replace("-", "−"), x, 414, 34, color, lettering)
    x += paint_text(ctx, "°F" if fahrenheit else "°C", x + 3, 414, 32, color, lettering)
    if degrees <= (35 if fahrenheit else 2):
        snowflake(ctx, x + 25, 402, 14, color)


def parking_brake(ctx, lettering, ink):
    x, y = 1850, 41
    set_color(ctx, ink)
    ctx.set_line_width(3.1)
    ctx.new_path()
    ctx.arc(x, y, 15, 0, math.tau)
    ctx.stroke()
    for angle in (0, math.pi):
        ctx.arc(x, y, 22, angle - 0.75, angle + 0.75)
        ctx.stroke()
    paint_text(ctx, "P", x, y + 9, 24, ink, lettering, weight=1, align=0.5)


def power_meter(ctx, milliwatts, ink, track, regen):
    # Battery power is positive under regen in the fork's wire convention.
    x, neutral = 1785, 211
    set_color(ctx, track)
    ctx.rectangle(x, 105, 9, 210)
    ctx.fill()
    kw = milliwatts / 1_000_000
    length = min(abs(kw) / (100 if kw > 0 else 200), 1) * 104
    set_color(ctx, regen if kw > 0 else ink)
    ctx.rectangle(x, neutral if kw >= 0 else neutral - length, 9, length)
    ctx.fill()
    set_color(ctx, ink)
    ctx.move_to(x - 24, neutral - 21)
    for dx, dy in [(-40, 3), (-30, 3), (-34, 19), (-18, -6), (-28, -6)]:
        ctx.line_to(x + dx, neutral + dy)
    ctx.close_path()
    ctx.fill()


def charge_plug(ctx, x, y, height, ink):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(height / 32, height / 32)
    set_color(ctx, ink)
    ctx.set_line_width(3)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    for pin in (-7, 6):
        ctx.move_to(pin, -16)
        ctx.line_to(pin, -7)
    ctx.move_to(-12, -7)
    ctx.line_to(11, -7)
    ctx.arc(-0.5, -3, 10, 0, math.pi)
    ctx.close_path()
    ctx.move_to(0, 7)
    ctx.line_to(0, 16)
    ctx.stroke()
    ctx.restore()


def range_reading(fields):
    distance = number(fields, "range_m_aaos")
    unit = fields.get("distance_unit", "km")
    divisor = {"mi": 1609.344, "km": 1000, "m": 1}.get(unit)
    if distance is not None and distance >= 0 and divisor:
        return whole(distance / divisor), unit
    return None


def battery_percent(fields):
    energy = number(fields, "soc_aaos")
    capacity = number(fields, "usable_capacity_wh")
    if capacity is None or capacity <= 0:
        capacity = number(fields, "pack_capacity_wh")
    if energy is not None and energy >= 0 and capacity is not None and capacity > 0:
        return min(100, 100 * energy / capacity)
    return None


class PercentLabel:
    """A number and a smaller percent sign aligned at the bottom of their ink."""
    def __init__(self, ctx, value, size, lettering, sign_ratio=0.72):
        self.text = whole(value)
        self.size = size
        self.lettering = lettering
        digit_height, digit_bottom = lettering.digit_ink if lettering else (0.72, 0)
        sign_height, sign_bottom = lettering.percent_ink if lettering else (0.72, 0)
        self.sign_size = size * sign_ratio * digit_height / sign_height
        self.sign_y = size * digit_bottom - self.sign_size * sign_bottom
        self.sign_x = text_width(ctx, self.text, size, lettering) + size * (2 / 39)
        self.width = self.sign_x + text_width(ctx, "%", self.sign_size, lettering)
        self.baseline_from_center = size * (digit_height / 2 - digit_bottom)

    def paint(self, ctx, x, y, ink, suffix_ink=None):
        paint_text(ctx, self.text, x, y, self.size, ink, self.lettering)
        paint_text(ctx, "%", x + self.sign_x, y + self.sign_y, self.sign_size,
                   suffix_ink or ink, self.lettering)


def display_mode(fields):
    gear = fields.get("gear_selected")
    plugged = fields.get("charge_port_connected")
    speed = number(fields, "speed_display_aaos")
    if gear in ("D", "R", "N") or speed not in (None, 0):
        return "driving"
    if plugged is not False:
        state = fields.get("charge_state")
        if state in ("charging", "full", "fault"):
            return state
        if state != "idle":
            active = fields.get("charging_active")  # Older Android senders
            if active is True:
                return "charging"
            if (active is not False and plugged is True and gear == "P"
                    and (number(fields, "battery_power_mw") or 0) >= 100_000):
                return "charging"
        if plugged is True:
            return "plugged"
    if fields.get("before_drive") is True and gear == "P" and speed == 0:
        return "welcome"
    return "driving"


def charging_details(fields, mode):
    distance = range_reading(fields)
    if distance:
        yield distance
    if mode != "charging":
        return
    remaining = number(fields, "charge_seconds_remaining")
    if remaining is not None and remaining > 0:
        hours, minutes = divmod(math.ceil(remaining / 60), 60)
        duration = ["Done in"]
        if hours:
            duration.extend((str(hours), "h"))
        if minutes:
            duration.extend((str(minutes), "min"))
        yield duration
    power = number(fields, "battery_power_mw")
    if power is not None and power >= 100_000:
        kw = power / 1_000_000
        yield (f"{kw:.1f}".removesuffix(".0") if kw < 10 else whole(kw), "kW")


def paint_charging(ctx, fields, lettering, face_height, dark, mode):
    _, ink, secondary, *_ = NIGHT if dark else DAY
    if not dark:
        ink = "#2e2e2e"
    percent = battery_percent(fields)
    # In the EX90 illustration the bar runs from 21% to 82% of the instrument face.
    bar_top = HEIGHT / 2 - 0.29 * face_height
    bar_height = 0.61 * face_height
    bar_bottom = bar_top + bar_height
    if percent is not None and percent > 0:
        fill = "#2b7e49" if dark else "#3aaa62"
        if mode == "plugged":
            fill = "#626c78" if dark else "#d1d4d5"
        elif mode == "fault":
            fill = "#9e2a2b" if dark else "#e98989"
        alpha = 0.92 + 0.08 * math.cos(time.monotonic() * math.tau / 4) if mode == "charging" else 1
        set_color(ctx, fill, alpha)
        ctx.rectangle(0, bar_top, CHARGE_TRACK_WIDTH * percent / 100, bar_height)
        ctx.fill()

    set_color(ctx, ink)
    if mode == "charging":
        ctx.move_to(398, 146)
        for x, y in ((370, 188), (386, 188), (380, 215), (409, 171), (393, 171)):
            ctx.line_to(x, y)
        ctx.close_path()
        ctx.fill()
    elif mode == "plugged":
        charge_plug(ctx, 390, 181, 54, ink)
    elif mode == "full":
        ctx.set_line_width(5)
        ctx.move_to(367, 182)
        ctx.line_to(382, 197)
        ctx.line_to(413, 163)
        ctx.stroke()
    else:  # Charging fault
        ctx.set_line_width(3.5)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.move_to(390, 153)
        ctx.line_to(419, 204)
        ctx.line_to(361, 204)
        ctx.close_path()
        ctx.stroke()
        ctx.move_to(390, 170)
        ctx.line_to(390, 187)
        ctx.stroke()
        ctx.arc(390, 195, 2.4, 0, math.tau)
        ctx.fill()
    paint_text(ctx, CHARGE_TITLES[mode], 450, 218, 99, ink, lettering)
    x = 450
    for group in charging_details(fields, mode):
        for token in group:
            x += paint_text(ctx, token, x, 297, 42, ink, lettering) + 8
        x += 23

    # Keep the large reading's right edge from the original 90% layout at every target.
    reading_right = CHARGE_TRACK_WIDTH * 0.9 - 12
    if percent is None:
        paint_text(ctx, "–", reading_right, 256, 122, secondary, lettering, align=1)
    else:
        reading = PercentLabel(ctx, percent, 170, lettering, 0.25)
        reading.paint(ctx, reading_right - reading.width, 261, ink)
    if cold_pack(fields):
        snowflake(ctx, reading_right + 32, 248, 17, ink)

    target = number(fields, "charge_target_pct")
    if target is not None and 0 <= target <= 100:
        marker = CHARGE_TRACK_WIDTH * target / 100
        tick_height = 0.083 * face_height
        set_color(ctx, ink)
        ctx.rectangle(marker - 1.5, bar_bottom - tick_height, 3, tick_height)
        ctx.fill()
        limit = PercentLabel(ctx, target, 32, lettering)
        label_x = marker - 12 - limit.width
        if label_x < 0:
            label_x = marker + 12
        limit.paint(ctx, label_x, bar_bottom - tick_height / 2 + limit.baseline_from_center, ink)


def paint_energy(ctx, fields, lettering, dark, reading_x):
    _, ink, secondary, *_ = NIGHT if dark else DAY
    reading_ink = ink if dark else "#686868"
    distance = range_reading(fields)
    if distance:
        value, unit = distance
        advance = paint_text(ctx, value, reading_x, 202, 63, reading_ink, lettering)
        paint_text(ctx, unit, reading_x + advance + 5, 202, 33, reading_ink, lettering)

    percent = battery_percent(fields)
    low = fields.get("battery_low")
    cold = cold_pack(fields)
    if percent is not None or low is True or cold:
        battery(ctx, reading_x + 4, 237, percent, battery_ink(percent, low, dark))
        x = reading_x + 69
        if percent is None:
            x += paint_text(ctx, "–", x, 263, 39, reading_ink, lettering)
        else:
            label = PercentLabel(ctx, percent, 39, lettering)
            label.paint(ctx, x, 263, reading_ink, secondary)
            x += label.width
        if cold:
            snowflake(ctx, x + 24, 249, 14, reading_ink)


def paint_welcome(ctx, fields, lettering, dark):
    _, ink, secondary, *_ = NIGHT if dark else DAY
    paint_text(ctx, WELCOME_LABELS[0], 256, 213, 88, ink, lettering, weight=1)
    paint_text(ctx, WELCOME_LABELS[1], 256, 271, 32, secondary if dark else "#686868", lettering)
    paint_energy(ctx, fields, lettering, dark, 1410)


def paint_driving(ctx, fields, lettering, face_height, dark):
    _, ink, secondary, track, _, regen = NIGHT if dark else DAY
    speed = number(fields, "speed_display_aaos")
    unit = fields.get("speed_unit", "km/h")
    factor = {"mph": 3600 / 1609.344, "km/h": 3.6, "m/s": 1}.get(unit)
    if speed is not None and factor is not None:
        paint_speed(ctx, whole(abs(speed) * factor), face_height, ink, lettering)
        paint_text(ctx, unit, 954, 351, 37, ink, lettering, align=0.5)
    else:
        paint_text(ctx, "–", 954, 291, 210, ink, lettering, align=0.5)

    gear = fields.get("gear_selected")
    if gear in ("P", "R", "N", "D"):
        for i, letter in enumerate("PRND"):
            chosen = letter == gear
            paint_text(ctx, letter, 1868, 156 + i * 46, 37, ink if chosen else secondary,
                       lettering, weight=int(chosen), align=0.5)
    power = number(fields, "battery_power_mw")
    if power is not None:
        power_meter(ctx, power, ink, track, regen)
    if fields.get("charge_port_connected") is True:
        charge_plug(ctx, 46, 406, 32, secondary)


class FaceTransition:
    def __init__(self):
        self.mode = self.previous = None
        self.started = 0
        self.departure = 0
        self.welcome_fields = None

    def progress(self, mode, fields=None):
        now = time.monotonic()
        elapsed = min(1, (now - self.started) / 0.32)
        progress = elapsed * elapsed * (3 - 2 * elapsed)
        if mode == "welcome" or mode is None:
            self.welcome_fields = fields
        if mode != self.mode:
            self.departure = progress
            self.previous, self.mode = self.mode, mode
            self.started = now
            progress = 0
        if mode is None or (mode == "driving" and self.previous is None):
            return 1
        return progress


def fade(ctx, opacity, painter, *args):
    if opacity >= 1:
        painter(ctx, *args)
    elif opacity > 0:
        ctx.save()
        ctx.translate(0, FADE_OFFSET * (1 - opacity))
        ctx.push_group()
        painter(ctx, *args)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(opacity)
        ctx.restore()


def draw(ctx, width, height, fields, lettering=None, *, dark=False, message="", transition=None):
    bg, _, secondary, _, brake, _ = NIGHT if dark else DAY
    mode = display_mode(fields)
    progress = transition.progress(mode, fields) if transition else 1
    if mode in CHARGE_TITLES and not dark:
        bg = "#ebebeb"
    set_color(ctx, bg)
    ctx.paint()
    scale = min(width / WIDTH, height / HEIGHT)
    if scale <= 0:
        return False
    ctx.save()
    ctx.translate((width - WIDTH * scale) / 2, (height - HEIGHT * scale) / 2)
    ctx.scale(scale, scale)
    face_height = min(height / scale, WIDTH / 4)
    if mode in CHARGE_TITLES:
        fade(ctx, progress, paint_charging, fields, lettering, face_height, dark, mode)
    elif mode == "welcome":
        fade(ctx, progress, paint_welcome, fields, lettering, dark)
    else:
        leaving_welcome = progress < 1 and transition.previous == "welcome"
        paint_driving(ctx, fields, lettering, face_height, dark)
        fade(ctx, 1 if leaving_welcome else progress, paint_energy, fields, lettering, dark, 192)
        if leaving_welcome:
            # Dissolve the welcome face and its background together over the live instruments.
            ctx.push_group()
            set_color(ctx, bg)
            ctx.paint()
            ctx.translate(0, FADE_OFFSET * transition.departure * progress)
            fade(ctx, transition.departure, paint_welcome, transition.welcome_fields, lettering, dark)
            ctx.pop_group_to_source()
            ctx.paint_with_alpha(1 - progress)
    paint_outside_temperature(ctx, fields, lettering, dark)
    if fields.get("parking_brake") is True:
        parking_brake(ctx, lettering, brake)
    if message:
        paint_text(ctx, message, 960, 404, 30, secondary, align=0.5)
    ctx.restore()
    return progress < 1
