"""Read complete snapshots from the currently connected car."""
import json
import time

from cluster import Lettering

MAX_LINE = 384 * 1024


class Stream:
    def __init__(self):
        self.dark = True
        self.reset()

    def reset(self):
        self.buffer = bytearray()
        self.lettering = None
        self.fields = {}
        self.live = False
        self.deadline = time.monotonic() + 15  # includes the initial lettering transfer

    def feed(self, data):
        self.buffer.extend(data)
        while (end := self.buffer.find(b"\n")) >= 0:
            if end > MAX_LINE:
                raise ValueError("Oversized frame")
            frame = json.loads(self.buffer[:end])
            del self.buffer[:end + 1]
            if not isinstance(frame, dict):
                raise ValueError("Expected a frame")
            if frame.get("type") == "lettering" and self.lettering is None:
                self.lettering = Lettering(frame)
            elif frame.get("type") == "state" and self.lettering is not None:
                fields = frame["fields"]
                if not isinstance(fields, dict) or any(type(v) not in (str, int, float, bool) for v in fields.values()):
                    raise ValueError("Invalid vehicle fields")
                self.fields = fields
                if type(fields.get("night_mode")) is bool:
                    self.dark = fields["night_mode"]
                self.live = True
                self.deadline = time.monotonic() + 3
            else:
                raise ValueError("Unexpected frame order or type")
        if len(self.buffer) > MAX_LINE:
            raise ValueError("Unterminated frame")
