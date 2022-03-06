"""A UDP client."""

import socket
import random
from .. import util


class Client:
    """
    Create a client with a given server address and timeout interval.
    """

    def __init__(self, hostname: str, portnum: int, timeout_interval: float) -> None:
        """
        Initializes the client.

        Parameters
        ----------
        hostname : str
            The hostname of the server to contact.
        portnum : int
            The port number of the server to contact.
        timeout_interval : float
            The maximum time that can elapse between a timestamp for a timeout.
        """
        self._server_port = portnum
        self._server_hostname = util.get_hostname(hostname)
        self._server_ip_address = socket.gethostbyname(hostname)
        # self._server_session_id = -1
        self._session_id = random.randint(0, 2**32)
        self._seq = 0

        self._can_send_goodbye = True
        self._can_send_data = True
        self._waiting_for_hello = True
        self._closed = False

        self.timeout_interval = timeout_interval

    def is_waiting_for_hello(self) -> bool:
        """
        Returns True if the client is waiting for hello, False otherwise.

        Returns
        -------
        bool
            True if the client is waiting for hello, False otherwise
        """
        return self._waiting_for_hello

    def closed(self) -> bool:
        """
        Returns True if the client is closed, False otherwise.

        Returns
        -------
        bool
            True if the client is closed, False otherwise
        """
        return self._closed
