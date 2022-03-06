# pylint: disable=unused-argument
"""An event-based client."""

import pyuv
from typing import Callable  # pylint: disable=unused-import
from ..constants import Command
from . import Client
from .. import constants
from .. import util


class EventClient(Client):
    """
    Create an event-based client with a given server address and timeout interval.
    """

    def __init__(self, hostname: str, portnum: int, timeout_interval: float, loop,
                 close_cb: "Callable[[],None]") -> None:
        """
        Initializes the client and creates a timer and socket.

        Parameters
        ----------
        hostname : str
            The hostname of the server to contact.
        portnum : int
            The port number of the server to contact.
        timeout_interval : float
            The maximum time that can elapse between a timestamp for a timeout.
        loop
            The pyuv event loop.
        close_cb : Callable[[],None]
            The function to be called when the client closes.
        """
        super().__init__(hostname, portnum, timeout_interval)

        self._socket = pyuv.UDP(loop)
        self._socket.start_recv(self.handle_packet)

        self._timer = pyuv.Timer(loop)
        self._timer_active = False

        self._close_cb = close_cb

    def _reset_timer(self) -> None:
        if self._timer_active:
            self._timer.stop()
        return super()._reset_timer()

    def _start_timer(self) -> None:
        if not self._timer_active:
            if self.timeout_interval > 0:
                self._timer.start(self.timed_out, self.timeout_interval, 0)
        return super()._start_timer()

    def _send_packet(self, command: int, data: "str|None" = None) -> bytes:
        """
        Sends a packet to the associated server of this client.

        This method will also increment the client's sequence number by one.

        Parameters
        ----------
        command : int
            The command integer value.
        data : str | None
            The string to send with the packet. Default value is None.
        """
        packet = super()._send_packet(command, data)
        self._socket.send((self._server_ip_address, self._server_port), packet)
        return packet

    def timed_out(self, handle=None) -> None:
        """
        Attempt to check if the client has timed out.

        If the server is not closed, the client will check the last timestamp recorded with the current time and see
        if it surpasses the client's timeout interval. Otherwise, None is returned.

        Will send a GOODBYE to the server if the client has not sent one yet, otherwise it closes.

        Returns
        -------
        bool | None
            Returns None is the client is closed. Returns True if the duration of last timestamp recorded exceeds
            the client's timeout interval.
        """
        if not self.closed():
            print("timed out")
            # anytime we timeout, we're definitely not waiting for hello anymore
            self._waiting_for_hello = False

            goodbye = self._can_send_goodbye

            if goodbye:
                self.send_goodbye()
            else:
                self.close()

    def signal_close(self) -> None:
        self.close()

    def close(self) -> None:
        """
        Closes the client's socket.

        Also prevents calls to timed_out() and handle_packet() from processing timeouts and packets, respectively.
        """
        self._can_send_goodbye = False
        self._can_send_data = False
        self._closed = True

        self._socket.stop_recv()
        self._timer.stop()
        self._timer_active = False

        self._close_cb()

    def handle_packet(self,
                        handle=None,
                        address: "tuple[str,int]" = None,
                        flags=None,
                        packet: bytes = None,
                        error=None) -> None:
        super().handle_packet(packet, address)