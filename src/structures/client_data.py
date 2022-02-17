from typing import Any


class ClientData:
    session_id: int
    connected: bool
    packet_number: int
    address: Any
    timestamp: float

    def __init__(self, session_id: int, address: Any):
        self.session_id = session_id
        self.connected = True
        self.packet_number = 0
        self.address = address
        self.timestamp = -1

    def __del__(self):
        print("0x%08x %s" % (self.session_id, "Session Closed"))

    def disconnect(self):
        self.connected = False