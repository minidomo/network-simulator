# pylint: disable=unused-argument
"""An event-based client."""

import pyuv
from typing import Callable  # pylint: disable=unused-import
from . import Client


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
        loop : pyuv.Loop
            The pyuv event loop.
        close_cb : Callable[[],None]
            The callback function to be called when the client closes.
        """
        super().__init__(hostname, portnum, timeout_interval)

        self._socket = pyuv.UDP(loop)
        self._socket.start_recv(self.handle_packet)

        self._timer = pyuv.Timer(loop)
        self._timer_active = False

        self._close_cb = close_cb

    def _try_stop_timer(self) -> None:
        if self._timer_active:
            self._timer.stop()
            self._timer_active = False

    def _try_start_timer(self) -> None:
        if not self._timer_active:
            if self.timeout_interval > 0:
                self._timer.start(self.timed_out, self.timeout_interval, 0)
            self._timer_active = True

    def _send(self, data: bytes) -> None:
        self._socket.send((self._server_ip_address, self._server_port), data)

    def signal_close(self) -> None:
        self.close()

    def close(self) -> None:
        self._can_send_goodbye = False
        self._can_send_data = False
        self._closed = True

        self._socket.stop_recv()
        self._try_stop_timer()

        self._close_cb()

    def handle_packet(self,
                      handle=None,
                      address: "tuple[str,int]" = None,
                      flags=None,
                      packet: bytes = None,
                      error=None) -> None:
        super().handle_packet(packet, address)

    def timed_out(self, handle=None) -> None:
        """
        Processes the event where a timeout has occurred.

        If a GOODBYE packet has not been sent to the server, a GOODBYE packet will be sent to the server. Otherwise
        the client will close.
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
