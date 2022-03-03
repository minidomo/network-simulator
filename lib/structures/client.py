"""A thread-based client."""

import socket as _socket
import random as _random
import threading as _threading
from queue import Queue as _Queue
from time import time as _time
from .. import constants as _Constants
from .. import util as _util


class Client:
    """
    Create a thread-based client with a given server address and timeout interval.
    """

    def __init__(self, hostname: str, portnum: int, timeout_interval: int) -> None:
        """
        Initializes the client.

        Parameters
        ----------
        hostname : str
            The hostname of the server to contact.
        portnum : int
            The port number of the server to contact.
        timeout_interval : int
            The maximum time that can elapse between a timestamp for a timeout.
        """
        self._socket = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        self._server_address = (hostname, portnum)
        self._server_session_id = -1
        self._session_id = _random.randint(0, 2**32)
        self._seq = 0
        self._signal_queue = _Queue()
        self._waiting_hello = True
        self._time_out_count = 0

        self._can_send_goodbye = True
        self._can_send_data = True
        self._can_send_lock = _threading.Lock()
        self._can_send_goodbye_lock = _threading.Lock()

        self._timestamp = -1
        self._timestamp_lock = _threading.Lock()

        self._closed = False
        self._closed_lock = _threading.Lock()

        self.timeout_interval = timeout_interval

    def closed(self) -> bool:
        """
        Returns True if the client is closed, false otherwise.
        """
        with self._closed_lock:
            return self._closed

    def wait_for_signal(self) -> _Constants.Signal:
        """
        Blocks the calling thread until a signal is received.

        Returns
        -------
        Signal
            Returns the first signal received.
        """
        return self._signal_queue.get()

    def signal_hello(self) -> None:
        """
        Sends a HELLO signal to a thread that is waiting for a signal.
        """
        self._signal_queue.put(_Constants.Signal.HELLO)

    def signal_close(self) -> None:
        """
        Sends a CLOSE signal to a thread that is waiting for a signal.

        Calling this method will prevent the client from sending goodbye and data packets to the server.
        """
        with self._can_send_lock:
            # in case we never call send_goodbye() - when server quits before client
            # prevent the client from sending goodbye and data packets
            self._can_send_goodbye = False
            self._can_send_data = False
        self._signal_queue.put(_Constants.Signal.CLOSE)

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
        encoded_data = _util.pack(command, self._seq, self._session_id, data)
        self._seq += 1
        self._socket.sendto(encoded_data, self._server_address)

    def send_hello(self) -> None:
        """
        Sends a HELLO packet to the associated server of this client.

        This method will also set a timestamp for when this packet was sent to be used in timed_out().
        """
        self._timestamp = _time()
        self._send_packet(_Constants.Command.HELLO.value)

    def send_data(self, text: str) -> None:
        """
        Sends a DATA packet to the associated server of this client.

        This method will also set a timestamp for when this packet was sent to be used in timed_out().

        Parameters
        ----------
        text : str
            The string to send with the packet.
        """
        with self._can_send_lock:
            if self._can_send_data:

                with self._timestamp_lock:
                    if self._timestamp == -1:
                        self._timestamp = _time()

                self._send_packet(_Constants.Command.DATA.value, text)

    def send_goodbye(self) -> None:
        """
        Sends a GOODBYE packet to the associated server of this client.

        This method will also set a timestamp for when this packet was sent to be used in timed_out().
        In addition, this will prevent the client from sending goodbye and data packets to the server.
        """
        with self._can_send_lock:
            with self._can_send_goodbye_lock:
                if self._can_send_goodbye:

                    with self._timestamp_lock:
                        self._timestamp = _time()

                    # prevent the client from sending goodbye and data packets
                    self._can_send_goodbye = False
                    self._can_send_data = False

                    self._send_packet(_Constants.Command.GOODBYE.value)

    def receive_packet(self) -> "tuple[bytes,tuple[str,int]]":
        """
        Returns a packet that was sent to the client.

        Will block the calling thread until a packet is received or client's socket is shutdown.

        Returns
        -------
        tuple[bytes,tuple[str,int]]
            The packet that was sent to the client.
        """
        return self._socket.recvfrom(_Constants.BUFFER_SIZE)

    def close(self) -> None:
        """
        Closes the client's socket.

        Also prevents calls to timed_out() and handle_packet() from processing timeouts and packets, respectively.
        """
        with self._closed_lock:
            self._closed = True

        try:
            # this will unblock calls to socket.recvfrom
            self._socket.shutdown(_socket.SHUT_RDWR)
        except:  # pylint: disable=bare-except
            pass
        self._socket.close()

    def timed_out(self) -> "bool|None":
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
            timeout = False
            with self._timestamp_lock:
                timeout = self._timestamp != -1 and _time() - self._timestamp > self.timeout_interval
            if timeout:
                print("timed out")
                self._time_out_count += 1
                if self._time_out_count == 1:
                    self.send_goodbye()
                else:
                    self.signal_close()
            return timeout

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
            magic_num, version, command, _, session_id = _util.unpack(packet)

            if magic_num == _Constants.MAGIC_NUMBER and version == _Constants.VERSION:

                # enters this only once for the hello exchange
                if self._waiting_hello:
                    self._waiting_hello = False
                    self._server_session_id = session_id

                    if command == _Constants.Command.HELLO.value:
                        self.signal_hello()
                    else:
                        print(f"expected hello, received {command}")
                        self.send_goodbye()
                        self.signal_close()
                    return

                # checks if the session id matches with the session id from the hello exchange
                # if not equal, assume server has become crazy
                if session_id != self._server_session_id:
                    print(f"different session id: {self._server_session_id} != {session_id}")
                    self.send_goodbye()
                    self.signal_close()
                    return

                # always close when receiving a goodbye from the client
                if command == _Constants.Command.GOODBYE.value:
                    print("GOODBYE from server.")
                    self.signal_close()
                    return

                # in all scenarios except for hello exchange, receiving alive is ok
                if command == _Constants.Command.ALIVE.value:
                    with self._can_send_goodbye_lock:
                        with self._timestamp_lock:
                            # only reset timestamp for alive when client is not in closing state
                            # if _can_send_goodbye is False, client is in closing state
                            if self._timestamp != -1 and self._can_send_goodbye:
                                self._timestamp = -1
                    return

                # assume server has gone crazy
                print(f"Invalid command: {command}")
                self.send_goodbye()
                self.signal_close()
