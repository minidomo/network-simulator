from ..constants import Command


class ClientData:
    session_id: int
    connected: bool
    packet_number: int
    address: "tuple[str,int]"
    timestamp: float
    previous_command: int

    def __init__(self, session_id: int, address: "tuple[str,int]"):
        self.session_id = session_id
        self.connected = True
        self.packet_number = 0
        self.address = address
        self.timestamp = -1
        self.previous_command = Command.DEFAULT.value

    def disconnect(self):
        self.connected = False
