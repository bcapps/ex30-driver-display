#!/usr/bin/env python3
"""Fullscreen instrument display for Raspberry Pi OS."""
import dbus
import gi
from dbus.mainloop.glib import DBusGMainLoop

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from bluez import Receiver
from cluster import FaceTransition, draw
from stream import Stream


def main():
    DBusGMainLoop(set_as_default=True)
    window = Gtk.Window(title="EX30 Driver Display")
    window.set_decorated(False)
    area = Gtk.DrawingArea()
    window.add(area)
    stream = Stream()
    receiver = Receiver(dbus.SystemBus(), stream, area.queue_draw)
    transition = FaceTransition()
    timer = interval = 0

    def refresh():
        nonlocal timer, interval
        timer = interval = 0
        area.queue_draw()
        return False

    def paint(widget, ctx):
        nonlocal timer, interval
        if not stream.live:
            transition.progress(None)
        animating = draw(ctx, widget.get_allocated_width(), widget.get_allocated_height(), stream.fields,
                         stream.lettering, dark=stream.dark, message="" if stream.live else receiver.waiting,
                         transition=transition if stream.live else None)
        delay = 16 if animating else 125 if transition.mode == "charging" else 0
        if delay != interval:
            if timer:
                GLib.source_remove(timer)
            interval = delay
            timer = GLib.timeout_add(delay, refresh) if delay else 0
        return False

    area.connect("draw", paint)
    window.connect("destroy", Gtk.main_quit)
    window.fullscreen()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
