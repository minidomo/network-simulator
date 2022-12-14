"""A UDP client."""

import socket
import random
from abc import ABC, abstractmethod
from ..constants import Command
from .. import util
from .. import constants


class Client(ABC):
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
        self._session_id = random.randint(0, 2**32)
        self._seq = 0

        self._can_send_goodbye = True
        self._can_send_data = True
        self._waiting_for_hello = True
        self._closed = False

        self.timeout_interval = timeout_interval
        self._timer_active = False

    @abstractmethod
    def _try_stop_timer(self) -> None:
        """
        Attempts to stop the timer if currently running.
        """
        pass

    @abstractmethod
    def _try_start_timer(self) -> None:
        """
        Attempts to start the timer if not currently running.
        """
        pass

    @abstractmethod
    def _send(self, data: bytes) -> None:
        """
        Sends the given data to the server.
        """
        pass

    @abstractmethod
    def signal_close(self) -> None:
        """
        Will try to close the client and send a closing signal if necessary.

        Calling this method will prevent the client from sending goodbye and data packets to the server.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Closes the client's socket.

        Also prevents calls to timed_out() and handle_packet() from processing timeouts and packets, respectively.
        """
        pass

    def is_waiting_for_hello(self) -> bool:
        """
        Returns True if the client is waiting for hello, False otherwise.

        Returns
        -------
        bool
            True if the client is waiting for hello, False otherwise.
        """
        return self._waiting_for_hello

    def closed(self) -> bool:
        """
        Returns True if the client is closed, False otherwise.

        Returns
        -------
        bool
            True if the client is closed, False otherwise.
        """
        return self._closed

    def _send_packet(self, command: int, data: "str|None" = None) -> None:
        """
        Creates and sends a packet to the associated server of this client.

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
        self._send(encoded_data)

    def send_hello(self) -> None:
        """
        Sends a HELLO packet to the associated server of this client.

        This method will also start the timer.
        """
        # start timer
        self._try_start_timer()
        self._send_packet(Command.HELLO.value)

    def send_data(self, text: str) -> None:
        """
        Sends a DATA packet to the associated server of this client.

        This method will also start the timer if not already started.

        Parameters
        ----------
        text : str
            The string to send with the packet.
        """
        if self._can_send_data and not self.is_waiting_for_hello():
            # start timer if not set
            self._try_start_timer()
            self._send_packet(Command.DATA.value, text)

    def send_goodbye(self) -> None:
        """
        Sends a GOODBYE packet to the associated server of this client.

        This method will also stop and start the timer. In addition, this will prevent the client from sending
        goodbye and data packets to the server.
        """
        if self._can_send_goodbye:

            # start timer
            self._try_stop_timer()
            self._try_start_timer()

            # prevent the client from sending goodbye and data packets
            self._can_send_goodbye = False
            self._can_send_data = False

            self._send_packet(Command.GOODBYE.value)

    def hello_exchange(self, command) -> bool:
        """
        This method should only be called once.

        Handles a HELLO packet if we were waiting for a HELLO from the server.

        If any other packet was received while we are waiting for a HELLO,
        a protocol error occured and the client closes.

        Returns
        -------
        bool
            True if the client was waiting for a HELLO from the server, False otherwise.
        """
        if self._waiting_for_hello:
            self._waiting_for_hello = False

            self._try_stop_timer()

            if command != Command.HELLO.value:
                print(f"expected hello, received {command}")
                self.send_goodbye()
                self.signal_close()

            return True
        return False

    def handle_alive(self) -> None:
        """
        Handle an ALIVE packet.

        This method will also stop the timer if currently running.
        """
        # only reset timestamp for alive when client is not in closing state
        # if _can_send_goodbye is False, client is in closing state
        if self._can_send_goodbye:
            self._try_stop_timer()

    def handle_packet(self, packet: bytes, address: "tuple[str,int]") -> None:  # pylint: disable=unused-argument
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

            # checks if the session id matches with the session id from the hello exchange
            # if not equal, assume server has become crazy
            if self._session_id != session_id:
                print(f"different session id: {self._session_id} != {session_id}")
                self.send_goodbye()
                self.signal_close()
                return

            if magic_num == constants.MAGIC_NUMBER and version == constants.VERSION:

                # enters this only once for the hello exchange
                if self.hello_exchange(command):
                    return

                # always close when receiving a goodbye from the client
                if command == Command.GOODBYE.value:
                    print("GOODBYE from server.")
                    self.signal_close()
                    return

                # in all scenarios except for hello exchange, receiving alive is ok
                if command == Command.ALIVE.value:
                    self.handle_alive()
                    return

                # assume server has gone crazy
                print(f"Invalid command: {command}")
                self.send_goodbye()
                self.signal_close()
