#!/usr/bin/env python3
"""Fullscreen instrument display for Raspberry Pi OS."""
import dbus
import gi
from dbus.mainloop.glib import DBusGMainLoop

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from bluez import Receiver
from cluster import draw
from stream import Stream


def main():
    DBusGMainLoop(set_as_default=True)
    window = Gtk.Window(title="EX30 Driver Display")
    window.set_decorated(False)
    area = Gtk.DrawingArea()
    window.add(area)
    stream = Stream()
    receiver = Receiver(dbus.SystemBus(), stream, area.queue_draw)

    def paint(widget, ctx):
        draw(ctx, widget.get_allocated_width(), widget.get_allocated_height(), stream.fields,
             stream.lettering, dark=stream.dark, message="" if stream.live else receiver.waiting)
        return False

    area.connect("draw", paint)
    window.connect("destroy", Gtk.main_quit)
    window.fullscreen()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
