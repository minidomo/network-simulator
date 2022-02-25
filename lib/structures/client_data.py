from ..constants import Command as _Command


class ClientData:

    def __init__(self, session_id: int, address: "tuple[str,int]"):
        self.session_id: int = session_id
        self.connected: bool = True
        self.packet_number: int = 0
        self.address: "tuple[str,int]" = address
        self.timestamp: int = -1
        self.previous_command: int = _Command.DEFAULT.value

    def disconnect(self):
        self.connected = False
