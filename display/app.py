#!/usr/bin/env python3
"""Fullscreen instrument display for Raspberry Pi OS."""
import dbus
import gi
from dbus.mainloop.glib import DBusGMainLoop

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from bluez import Receiver
from cluster import draw, is_charging
from stream import Stream


def main():
    DBusGMainLoop(set_as_default=True)
    window = Gtk.Window(title="EX30 Driver Display")
    window.set_decorated(False)
    area = Gtk.DrawingArea()
    window.add(area)
    stream = Stream()
    receiver = Receiver(dbus.SystemBus(), stream, area.queue_draw)
    pulse_pending = False

    def next_pulse():
        nonlocal pulse_pending
        pulse_pending = False
        area.queue_draw()
        return False

    def paint(widget, ctx):
        nonlocal pulse_pending
        draw(ctx, widget.get_allocated_width(), widget.get_allocated_height(), stream.fields,
             stream.lettering, dark=stream.dark, message="" if stream.live else receiver.waiting)
        if not pulse_pending and is_charging(stream.fields):
            pulse_pending = True
            GLib.timeout_add(125, next_pulse)
        return False

    area.connect("draw", paint)
    window.connect("destroy", Gtk.main_quit)
    window.fullscreen()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
