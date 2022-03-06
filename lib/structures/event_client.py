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
        super().__init__(hostname, portnum, timeout_interval)

        self._socket = pyuv.UDP(loop)
        self._socket.start_recv(self.handle_packet)

        self._timer = pyuv.Timer(loop)
        self._timer_active = False

        self._close_cb = close_cb

    def _send_packet(self, command: int, data: "str|None" = None) -> None:
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
        encoded_data = util.pack(command, self._seq, self._session_id, data)
        self._seq += 1
        self._socket.send((self._server_ip_address, self._server_port), encoded_data)

    def send_hello(self) -> None:
        """
        Sends a HELLO packet to the associated server of this client.

        This method will also set a timestamp for when this packet was sent to be used in timed_out().
        """
        # start timer
        if self.timeout_interval > 0:
            self._timer.start(self.timed_out, self.timeout_interval, 0)
        self._timer_active = True

        self._send_packet(Command.HELLO.value)

    def send_data(self, text: str) -> None:
        """
        Sends a DATA packet to the associated server of this client.

        This method will also set a timestamp for when this packet was sent to be used in timed_out().

        Parameters
        ----------
        text : str
            The string to send with the packet.
        """
        if self._can_send_data:

            # start timer if not set
            if not self._timer_active:
                if self.timeout_interval > 0:
                    self._timer.start(self.timed_out, self.timeout_interval, 0)
                self._timer_active = True

            self._send_packet(Command.DATA.value, text)

    def send_goodbye(self) -> None:
        """
        Sends a GOODBYE packet to the associated server of this client.

        This method will also set a timestamp for when this packet was sent to be used in timed_out().
        In addition, this will prevent the client from sending goodbye and data packets to the server.
        """
        if self._can_send_goodbye:

            # start timer
            self._timer.stop()
            if self.timeout_interval > 0:
                self._timer.start(self.timed_out, self.timeout_interval, 0)
            self._timer_active = True

            # prevent the client from sending goodbye and data packets
            self._can_send_goodbye = False
            self._can_send_data = False

            self._send_packet(Command.GOODBYE.value)

    def handle_packet(self,
                      handle=None,
                      address: "tuple[str,int]" = None,
                      flags=None,
                      packet: bytes = None,
                      error=None) -> None:
        """
        Attempt to process the given packet.

        If the client is not closed, the client will process the packet with respect to the client's current state.

        Parameters
        ----------
        packet : bytes
            The packet to process.
        address : tuple[str,int]
            The address from where this packet originated.
        """
        if not self.closed():
            # only consider packets from the server and proper size
            if (address[0] != self._server_ip_address or address[1] != self._server_port or
                    len(packet) < constants.HEADER_SIZE):
                return

            magic_num, version, command, _, session_id = util.unpack(packet)

            if magic_num == constants.MAGIC_NUMBER and version == constants.VERSION:

                # enters this only once for the hello exchange
                if self._waiting_for_hello:
                    self._waiting_for_hello = False
                    self._server_session_id = session_id

                    # reset timer
                    self._timer.stop()
                    self._timer_active = False

                    if command != Command.HELLO.value:
                        print(f"expected hello, received {command}")
                        self.send_goodbye()
                        self.close()
                    return

                # checks if the session id matches with the session id from the hello exchange
                # if not equal, assume server has become crazy
                if self._server_session_id not in (-1, session_id):
                    print(f"different session id: {self._server_session_id} != {session_id}")
                    self.send_goodbye()
                    self.close()
                    return

                # always close when receiving a goodbye from the client
                if command == Command.GOODBYE.value:
                    print("GOODBYE from server.")
                    self.close()
                    return

                # in all scenarios except for hello exchange, receiving alive is ok
                if command == Command.ALIVE.value:
                    # only reset timer for alive when client is not in closing state
                    # if _can_send_goodbye is False, client is in closing state
                    if self._timer_active and self._can_send_goodbye:
                        self._timer.stop()
                        self._timer_active = False
                    return

                # assume server has gone crazy
                print(f"Invalid command: {command}")
                self.send_goodbye()
                self.close()

    def timed_out(self, handle=None) -> None:
        """
        Attempt to check if the client has timed out.

        If the server is not closed, the client will check the last timestamp recorded with the current time and see
        if it surpasses the client's timeout interval. Otherwise, None is returned.

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
