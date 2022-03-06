"""A thread-based client."""

import socket
from threading import Lock
from queue import Queue
from time import time
from . import Client
from ..constants import Command
from .. import constants
from .. import util


class ThreadClient(Client):
    """
    Create a thread-based client with a given server address and timeout interval.
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
        super().__init__(hostname, portnum, timeout_interval)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._signal_queue = Queue()

        self._can_send_lock = Lock()
        self._can_send_goodbye_lock = Lock()
        self._waiting_for_hello_lock = Lock()
        self._closed_lock = Lock()

        self._timestamp = -1
        self._timestamp_lock = Lock()

    def is_waiting_for_hello(self) -> bool:
        """
        Returns True if the client is waiting for hello, False otherwise.

        Returns
        -------
        bool
            True if the client is waiting for hello, False otherwise
        """
        with self._waiting_for_hello_lock:
            return super().is_waiting_for_hello()

    def closed(self) -> bool:
        """
        Returns True if the client is closed, False otherwise.

        Returns
        -------
        bool
            True if the client is closed, False otherwise
        """
        with self._closed_lock:
            return super().closed()

    def wait_for_signal(self) -> None:
        """
        Blocks the calling thread until a signal is received.
        """
        self._signal_queue.get()

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
        self._signal_queue.put(None)

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
        self._socket.sendto(packet, (self._server_ip_address, self._server_port))
        return packet

    def _reset_timer(self) -> None:
        with self._timestamp_lock:
            if self._timer_active:
                self._timestamp = -1
            super()._reset_timer()

    def _start_timer(self) -> None:
        with self._timestamp_lock:
            if self._timestamp == -1:
                self._timestamp = time()
                super()._start_timer()

    def send_data(self, text: str) -> None:
        with self._can_send_lock:
            super().send_data(text)

    def send_goodbye(self) -> None:
        with self._can_send_lock:
            with self._can_send_goodbye_lock:
                super().send_goodbye()

    def receive_packet(self) -> "tuple[bytes,tuple[str,int]]":
        """
        Listens on the client's socket for a packet.

        Will block the calling thread until a packet is received or client's socket is shutdown.

        Returns
        -------
        tuple[bytes,tuple[str,int]]
            The packet that was sent to the client.
        """
        return self._socket.recvfrom(constants.BUFFER_SIZE)

    def close(self) -> None:
        """
        Closes the client's socket.

        Also prevents calls to timed_out() and handle_packet() from processing timeouts and packets, respectively.
        """
        with self._closed_lock:
            self._closed = True

        self._reset_timer()

        try:
            # this will unblock calls to socket.recvfrom
            self._socket.shutdown(socket.SHUT_RDWR)
        except:  # pylint: disable=bare-except
            pass
        self._socket.close()

    def timed_out(self) -> "bool|None":
        """
        Attempt to check if the client has timed out.

        If the server is not closed, the client will check the last timestamp recorded with the current time and see
        if it surpasses the client's timeout interval. Otherwise, None is returned.

        Will send a GOODBYE message to the server if a DATA packet times out. Otherwise, if a GOODBYE has already been
        sent, it will signal the client to close.

        Returns
        -------
        bool | None
            Returns None is the client is closed. Returns True if the duration of last timestamp recorded exceeds
            the client's timeout interval.
        """
        if not self.closed():
            timeout = False
            with self._timestamp_lock:
                timeout = self._timestamp != -1 and time() - self._timestamp > self.timeout_interval
            if timeout:
                print("timed out")
                # anytime we timeout, we're definitely not waiting for hello anymore
                with self._waiting_for_hello_lock:
                    self._waiting_for_hello = False

                # if we have not yet sent goodbye, send it. otherwise, close.
                goodbye = False
                with self._can_send_goodbye_lock:
                    goodbye = self._can_send_goodbye

                if goodbye:
                    self.send_goodbye()
                else:
                    self.signal_close()
            return timeout

    def hello_exchange(self, command) -> bool:
        with self._waiting_for_hello_lock:
            return super().hello_exchange(command)

    def handle_alive(self) -> None:
        with self._can_send_goodbye_lock:
            return super().handle_alive()
