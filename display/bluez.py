"""One authenticated Bluetooth Classic profile for a dedicated display."""
import os
import socket
import time
from pathlib import Path

import cairo
import dbus
import dbus.service
from gi.repository import GLib

SERVICE = "9e457bc1-0291-4dcb-8427-919da22db81f"
PATH = "/com/bcapps/EX30Display"
BLUEZ = "org.bluez"
ADAPTER, DEVICE, AGENT, PROFILE = (BLUEZ + "." + name for name in ("Adapter1", "Device1", "Agent1", "Profile1"))
PROPS = "org.freedesktop.DBus.Properties"
WINDOW = 180


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Receiver(dbus.service.Object):
    def __init__(self, bus, stream, redraw):
        super().__init__(bus, PATH)
        self.bus, self.stream, self.redraw = bus, stream, redraw
        self.bluez = bus.get_name_owner(BLUEZ)
        self.owner_file = Path(os.environ["STATE_DIRECTORY"]) / "car"
        self.owner = self.owner_file.read_text().strip() if self.owner_file.exists() else None
        self.link = None
        self.device = None
        self.watch = None
        self.open_until = time.monotonic() + WINDOW
        root = bus.get_object(BLUEZ, "/")
        objects = dbus.Interface(root, "org.freedesktop.DBus.ObjectManager").GetManagedObjects()
        adapter_path = next((p for p, interfaces in objects.items() if ADAPTER in interfaces), None)
        if not adapter_path:
            raise RuntimeError("Waiting for Bluetooth adapter")
        self.adapter = dbus.Interface(bus.get_object(BLUEZ, adapter_path), PROPS)
        suffix = str(objects[adapter_path][ADAPTER]["Address"]).replace(":", "")[-4:]
        self.name = "EX30 Display " + suffix
        self.adapter.Set(ADAPTER, "Powered", dbus.Boolean(True))
        self.adapter.Set(ADAPTER, "Alias", self.name)
        manager = bus.get_object(BLUEZ, "/org/bluez")
        agents = dbus.Interface(manager, BLUEZ + ".AgentManager1")
        agents.RegisterAgent(PATH, "NoInputNoOutput")
        agents.RequestDefaultAgent(PATH)
        dbus.Interface(manager, BLUEZ + ".ProfileManager1").RegisterProfile(PATH, SERVICE, {
            "Name": self.name, "Role": "server", "Channel": dbus.UInt16(22),
            "RequireAuthentication": dbus.Boolean(True), "RequireAuthorization": dbus.Boolean(False),
        })
        self.adapter.Set(ADAPTER, "PairableTimeout", dbus.UInt32(WINDOW))
        self.adapter.Set(ADAPTER, "DiscoverableTimeout", dbus.UInt32(WINDOW))
        self.pairable(self.owner is None)
        bus.add_signal_receiver(self.daemon_changed, signal_name="NameOwnerChanged",
                                dbus_interface="org.freedesktop.DBus", arg0=BLUEZ)
        GLib.timeout_add(250, self.tick)

    def daemon_changed(self, name, old, new):
        if old == self.bluez:
            # systemd starts a fresh process to register with the new daemon.
            from gi.repository import Gtk
            Gtk.main_quit()

    @property
    def waiting(self):
        if self.owner:
            return "Waiting for car"
        if time.monotonic() < self.open_until:
            return "Select " + self.name + " in the car"
        return "Restart display to pair"

    def pairable(self, enable):
        for setting in ("Pairable", "Discoverable"):
            # Powering up can leave a management command pending for a moment.
            for attempt in range(10):
                if bool(self.adapter.Get(ADAPTER, setting)) == enable:
                    break
                try:
                    self.adapter.Set(ADAPTER, setting, dbus.Boolean(enable))
                    break
                except dbus.DBusException as error:
                    if error.get_dbus_name() != BLUEZ + ".Error.Busy" or attempt == 9:
                        raise
                    time.sleep(0.1)

    def peer(self, device, sender):
        if sender != self.bluez:
            raise Rejected("Expected Bluetooth service")
        props = dbus.Interface(self.bus.get_object(BLUEZ, device), PROPS).GetAll(DEVICE)
        address = str(props["Address"])
        if self.owner != address and (self.owner is not None or time.monotonic() >= self.open_until):
            raise Rejected("Display is paired or pairing has closed")
        return address, props

    @dbus.service.method(AGENT, in_signature="o", out_signature="", sender_keyword="sender")
    def RequestAuthorization(self, device, sender=None):
        self.peer(device, sender)

    @dbus.service.method(AGENT, in_signature="ou", out_signature="", sender_keyword="sender")
    def RequestConfirmation(self, device, passkey, sender=None):
        self.peer(device, sender)

    @dbus.service.method(AGENT, in_signature="os", out_signature="", sender_keyword="sender")
    def AuthorizeService(self, device, uuid, sender=None):
        if uuid.lower() != SERVICE:
            raise Rejected("Unexpected service")
        self.peer(device, sender)

    @dbus.service.method(AGENT, in_signature="", out_signature="")
    def Cancel(self):
        pass

    @dbus.service.method(PROFILE, in_signature="oha{sv}", out_signature="", sender_keyword="sender")
    def NewConnection(self, device, fd, properties, sender=None):
        address, props = self.peer(device, sender)
        if self.link or not props.get("Paired"):
            raise Rejected("Expected a bonded car and an idle display")
        if not self.owner:
            temp = self.owner_file.with_suffix(".tmp")
            temp.write_text(address + "\n")
            temp.replace(self.owner_file)
            self.owner = address
            self.pairable(False)
        self.device = device
        self.link = socket.socket(fileno=fd.take())
        self.link.setblocking(False)
        self.stream.reset()
        self.watch = GLib.io_add_watch(self.link.fileno(), GLib.PRIORITY_DEFAULT,
                                       GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP, self.read)

    @dbus.service.method(PROFILE, in_signature="o", out_signature="", sender_keyword="sender")
    def RequestDisconnection(self, device, sender=None):
        if sender == self.bluez and self.device == device:
            self.disconnect()

    def read(self, source, condition):
        try:
            data = self.link.recv(65536)
            if not data or condition & (GLib.IO_ERR | GLib.IO_HUP):
                self.disconnect()
                return False
            self.stream.feed(data)
            if self.stream.live:
                self.redraw()
        except BlockingIOError:
            return True
        except (OSError, ValueError, TypeError, KeyError, RecursionError, cairo.Error) as error:
            print("Closed invalid display stream:", error, flush=True)
            self.disconnect()
            return False
        return True

    def disconnect(self):
        if self.watch is not None:
            GLib.source_remove(self.watch)
            self.watch = None
        if self.link:
            # bluetoothd retains a duplicate of this fd. Shutdown reaches the
            # peer immediately even when only its heartbeat has stopped.
            try:
                self.link.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.link.close()
        self.link = self.device = None
        self.stream.reset()
        self.redraw()

    def tick(self):
        if self.link and time.monotonic() >= self.stream.deadline:
            self.disconnect()
        elif self.open_until and time.monotonic() >= self.open_until:
            self.open_until = 0
            if not self.owner:
                self.redraw()
        return True

    @dbus.service.method(PROFILE, in_signature="", out_signature="", sender_keyword="sender")
    def Release(self, sender=None):
        if sender == self.bluez:
            self.disconnect()
