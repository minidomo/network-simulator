"""A class containing information about clients for a server to utilize."""

from ..constants import Command as _Command


class ClientData:
    """
    Data about clients for a server.
    """

    def __init__(self, session_id: int, address: "tuple[str,int]"):
        """
        Creates an object containing client metadata.

        Parameters
        ----------
        session_id : int
            The session id of a client.
        address : tuple[str,int]
            The address of the client.
        """
        self.session_id: int = session_id
        self.connected: bool = True
        self.prev_packet_num: int = 0
        self.address: "tuple[str,int]" = address
        self.timestamp: int = -1
        self.prev_command_num: int = _Command.DEFAULT.value
