#!/usr/bin/env python3

import socket as _socket
import random as _random
import threading as _threading
from queue import Queue as _Queue
from time import time as _time
from .. import constants as _Constants
from .. import util as _util


class Client:

    def __init__(self, hostname: str, portnum: int) -> None:
        self._socket = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        self._server_address = (hostname, portnum)
        self._server_session_id = -1
        self._session_id = _random.randint(0, 2**32)
        self._seq = 0
        self._close_queue = _Queue()

        self._can_handle_packet = True
        self._can_handle_packet_lock = _threading.Lock()

        self._can_timed_out = True
        self._can_timed_out_lock = _threading.Lock()

        self._can_send_goodbye = True
        self._can_send_data = True
        self._can_send_lock = _threading.Lock()

        self._sent_data_num = 0
        self._sent_data_lock = _threading.Lock()

        self._timestamp = -1
        self._timestamp_lock = _threading.Lock()

        self.closed = False

    def wait_for_close_signal(self):
        self._close_queue.get()

    def signal_close(self):
        with self._can_send_lock:
            # in case we never call send_goodbye()
            self._can_send_goodbye = False
            self._can_send_data = False
        self._close_queue.put(None)

    def _send_packet(self, command: int, data: str = None) -> None:
        encoded_data = _util.pack(command, self._seq, self._session_id, data)
        self._seq += 1
        self._socket.sendto(encoded_data, self._server_address)

    def send_data(self, text: str) -> None:
        with self._can_send_lock:
            if self._can_send_data:

                with self._timestamp_lock:
                    if self._timestamp == -1:
                        self._timestamp = _time()

                with self._sent_data_lock:
                    self._sent_data_num += 1

                self._send_packet(_Constants.Command.DATA.value, text)

    def send_goodbye(self) -> None:
        with self._can_send_lock:
            if self._can_send_goodbye:

                with self._timestamp_lock:
                    self._timestamp = _time()

                self._can_send_goodbye = False
                self._can_send_data = False

                self._send_packet(_Constants.Command.GOODBYE.value)

    def receive_packet(self) -> "tuple[bytes,tuple[str,int]]":
        return self._socket.recvfrom(_Constants.BUFFER_SIZE)

    def close(self) -> None:
        self.closed = True

        with self._can_handle_packet_lock:
            self._can_handle_packet = False

        with self._can_timed_out_lock:
            self._can_timed_out = False

        try:
            self._socket.shutdown(_socket.SHUT_RDWR)
        except:  # pylint: disable=bare-except
            pass
        self._socket.close()

    def timed_out(self) -> "bool|None":
        proceed = False
        with self._can_timed_out_lock:
            proceed = self._can_timed_out

        if proceed:
            timeout = False
            with self._timestamp_lock:
                timeout = self._timestamp != -1 and _time() - self._timestamp > _Constants.TIMEOUT_INTERVAL
            if timeout:
                print("timed out")
                self.signal_close()
                return timeout
            return timeout

    def handle_packet(self, packet: bytes, address: "tuple[str,int]") -> None:
        proceed = False
        with self._can_handle_packet_lock:
            proceed = self._can_handle_packet

        if proceed:
            magic_num, version, command, _, session_id = _util.unpack(packet)

            if magic_num == _Constants.MAGIC_NUMBER and version == _Constants.VERSION:
                if session_id != self._server_session_id:
                    self.send_goodbye()
                    self.signal_close()
                    return

                if command == _Constants.Command.GOODBYE.value:
                    print("GOODBYE from server.")
                    self.signal_close()
                    return

                with self._sent_data_lock:
                    if command == _Constants.Command.ALIVE.value and self._sent_data_num > 0:
                        self._sent_data_num -= 1
                        with self._timestamp_lock:
                            if self._timestamp != -1:
                                self._timestamp = -1
                        return

                print(f"Invalid command: {command}")
                self.send_goodbye()
                self.signal_close()

    def hello_exchange(self) -> bool:
        # stop and wait
        def try_hello_exchange(result_queue: _Queue):
            self._send_packet(_Constants.Command.HELLO.value)
            while True:
                packet, _ = self._socket.recvfrom(_Constants.BUFFER_SIZE)
                magic_num, version, command, _, session_id = _util.unpack(packet)
                if magic_num == _Constants.MAGIC_NUMBER and version == _Constants.VERSION:
                    self._server_session_id = session_id
                    result_queue.put(command)
                    break

        queue = _Queue()
        t = _threading.Thread(target=try_hello_exchange, args=(queue,), daemon=True)
        t.start()

        try:
            command: int = queue.get(timeout=_Constants.TIMEOUT_INTERVAL)
            return command == _Constants.Command.HELLO.value
        except:  # pylint: disable=bare-except
            return False
