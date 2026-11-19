"""The Calm instrument face. All coordinates refer to its 1920 × 448 design."""
import base64
import io
import math
import struct

import cairo

WIDTH, HEIGHT = 1920, 448
# Sampled from Volvo's light and dark EX30 Calm reference images.
DAY = ("#f0f0f0", "#444444", "#969696", "#d6d6d6", "#c52631", "#22764c")
NIGHT = ("#2f3744", "#ffffff", "#99a5b3", "#717986", "#ff545b", "#69d99b")
LABELS = tuple("0123456789PRND") + ("km/h", "mph", "m/s", "mi", "km", "m", "%", "–")


def number(fields, key):
    value = fields.get(key)
    if type(value) in (int, float) and -3.403e38 <= value <= 3.403e38:
        return value
    return None


def whole(value):
    return str(math.floor(value + 0.5))


def set_color(ctx, color):
    ctx.set_source_rgb(*(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)))


class Lettering:
    """Monochrome text painted by Android. No font software is sent to the Pi."""
    def __init__(self, frame):
        if frame.get("version") != 1 or tuple(frame["labels"]) != LABELS:
            raise ValueError("Unsupported lettering")
        png = base64.b64decode(frame["png"], validate=True)
        if png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR" or png[16:24] != struct.pack(">II", 1920, 1536):
            raise ValueError("Unexpected lettering image size")
        widths = frame["advances"]
        if (len(widths) != 2 or any(len(row) != len(LABELS) for row in widths)
                or any(type(w) not in (int, float) or not 0 < w <= 320 for row in widths for w in row)):
            raise ValueError("Invalid label widths")
        self.surface = cairo.ImageSurface.create_from_png(io.BytesIO(png))
        self.widths = widths
        self.speed_row = frame.get("speedRow", 0)
        if type(self.speed_row) is not int or self.speed_row not in (0, 1):
            raise ValueError("Invalid speed lettering row")
        self.zero_ink = self.measure_zero()

    def measure_zero(self):
        # Measure visible ink once. The car's fallback font can have different proportions.
        tile = cairo.ImageSurface(cairo.FORMAT_A8, 320, 192)
        ctx = cairo.Context(tile)
        ctx.set_source_surface(self.surface, 0, -self.speed_row * 768)
        ctx.paint()
        tile.flush()
        mask = bytes(tile.get_data()).translate(bytes(128) + b"\xff" * 128)
        rows = [mask[y:y + 320] for y in range(0, len(mask), tile.get_stride())]
        ink = [(y, row.find(b"\xff"), row.rfind(b"\xff")) for y, row in enumerate(rows) if b"\xff" in row]
        if not ink:
            raise ValueError("Missing speed zero")
        left = min(left for _, left, _ in ink)
        right = max(right for _, _, right in ink) + 1
        bottom = ink[-1][0] + 1
        return right - left, bottom - ink[0][0], bottom - 174

    def draw(self, ctx, text, x, y, size, weight, align, tracking=0):
        indices = [LABELS.index(label) for label in ([text] if text in LABELS else text)]
        scales = [size / (216 if i < 10 else 128) for i in indices]
        advances = [self.widths[weight][i] * scale for i, scale in zip(indices, scales)]
        width = sum(advances) + tracking * (len(advances) - 1)
        ctx.save()
        ctx.translate(x - width * align, y)
        for i, scale, advance in zip(indices, scales, advances):
            baseline = 174 if i < 10 else 150
            ctx.save()
            ctx.scale(scale, scale)
            ctx.rectangle(-4, -baseline, 320, 192)
            ctx.clip()
            ctx.mask_surface(self.surface, -4 - i % 6 * 320, -baseline - weight * 768 - i // 6 * 192)
            ctx.restore()
            ctx.translate(advance + tracking, 0)
        ctx.restore()
        return width


def paint_text(ctx, text, x, y, size, color, lettering=None, weight=0, align=0):
    set_color(ctx, color)
    if lettering is not None:
        return lettering.draw(ctx, text, x, y, size, weight, align)
    # Setup messages and desktop previews can render before a car is paired.
    ctx.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if weight else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    width = ctx.text_extents(text)[4]
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
    ctx.rectangle(x + 3, y + 3, 44 * percent / 100, 18)
    ctx.fill()


def parking_brake(ctx, lettering, ink):
    x, y = 1850, 41
    set_color(ctx, ink)
    ctx.set_line_width(3.1)
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


def charge_plug(ctx, ink):
    set_color(ctx, ink)
    ctx.set_line_width(3)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(39, 390)
    ctx.line_to(39, 399)
    ctx.move_to(52, 390)
    ctx.line_to(52, 399)
    ctx.move_to(34, 399)
    ctx.line_to(57, 399)
    ctx.arc(45.5, 403, 10, 0, math.pi)
    ctx.close_path()
    ctx.move_to(46, 413)
    ctx.line_to(46, 422)
    ctx.stroke()


def draw(ctx, width, height, fields, lettering=None, *, dark=False, message=""):
    bg, ink, secondary, track, brake, regen = NIGHT if dark else DAY
    set_color(ctx, bg)
    ctx.paint()
    scale = min(width / WIDTH, height / HEIGHT)
    if scale <= 0:
        return
    ctx.save()
    ctx.translate((width - WIDTH * scale) / 2, (height - HEIGHT * scale) / 2)
    ctx.scale(scale, scale)

    speed = number(fields, "speed_display_aaos")
    unit = fields.get("speed_unit", "km/h")
    factor = {"mph": 3600 / 1609.344, "km/h": 3.6, "m/s": 1}.get(unit)
    available = speed is not None and factor is not None
    if available:
        # Keep the wide instrument face centred on taller monitors.
        paint_speed(ctx, whole(abs(speed) * factor), min(height / scale, WIDTH / 4), ink, lettering)
        paint_text(ctx, unit, 954, 351, 37, ink, lettering, align=0.5)
    else:
        paint_text(ctx, "–", 954, 291, 210, ink, lettering, align=0.5)

    distance = number(fields, "range_m_aaos")
    unit = fields.get("distance_unit", "km")
    divisor = {"mi": 1609.344, "km": 1000, "m": 1}.get(unit)
    if distance is not None and distance >= 0 and divisor:
        advance = paint_text(ctx, whole(distance / divisor), 1338, 202, 63, ink, lettering)
        paint_text(ctx, unit, 1343 + advance, 202, 33, ink, lettering)

    energy = number(fields, "soc_aaos")
    capacity = number(fields, "usable_capacity_wh")
    if capacity is None or capacity <= 0:
        capacity = number(fields, "pack_capacity_wh")
    if energy is not None and energy >= 0 and capacity is not None and capacity > 0:
        percent = min(100, 100 * energy / capacity)
        battery(ctx, 1342, 237, percent, ink)
        paint_text(ctx, whole(percent) + "%", 1407, 263, 39, ink, lettering)

    gear = fields.get("gear_selected")
    if gear in ("P", "R", "N", "D"):
        for i, letter in enumerate("PRND"):
            chosen = letter == gear
            paint_text(ctx, letter, 1868, 156 + i * 46, 37, ink if chosen else secondary,
                       lettering, weight=int(chosen), align=0.5)
    if fields.get("parking_brake") is True:
        parking_brake(ctx, lettering, brake)
    power = number(fields, "battery_power_mw")
    if power is not None:
        power_meter(ctx, power, ink, track, regen)
    if fields.get("charge_port_connected") is True:
        charge_plug(ctx, secondary)
    if message:
        paint_text(ctx, message, 960, 404, 30, secondary, align=0.5)
    ctx.restore()
