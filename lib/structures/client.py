#!/usr/bin/env python3

import socket as _socket
import random as _random
from queue import Queue as _Queue
from time import time as _time
from threading import Thread as _Thread, Lock as _Lock
from .. import constants as _Constants
from .. import util as _util


class Client:

    def __init__(self, hostname: str, portnum: int) -> None:
        self._socket = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        self._server_address = (hostname, portnum)
        self._server_session_id = -1
        self._session_id = _random.randint(0, 2**32)
        self._seq = 0
        self._timestamp = -1
        self._sent_data = False

        self._close_queue = _Queue()
        self._handle_packet_lock = _Lock()
        self._timed_out_lock = _Lock()

        self._can_send_goodbye = True
        self._can_send_data = True
        self._can_send_lock = _Lock()

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
        self._socket.sendto(encoded_data, self._server_address)
        self._seq += 1

    def send_data(self, text: str) -> None:
        with self._can_send_lock:
            if self._can_send_data:
                self._send_packet(_Constants.Command.DATA.value, text)

                if self._timestamp == -1:
                    self._timestamp = _time()
                self._sent_data = True

    def send_goodbye(self) -> None:
        with self._can_send_lock:
            if self._can_send_goodbye:
                self._send_packet(_Constants.Command.GOODBYE.value)

                self._timestamp = _time()
                self._can_send_goodbye = False
                self._can_send_data = False

    def receive_packet(self) -> "tuple[bytes,tuple[str,int]]":
        return self._socket.recvfrom(_Constants.BUFFER_SIZE)

    def close(self) -> None:
        self.closed = True
        self._handle_packet_lock.acquire()  # pylint: disable=consider-using-with
        self._timed_out_lock.acquire()  # pylint: disable=consider-using-with
        try:
            self._socket.shutdown(_socket.SHUT_RDWR)
        except:  # pylint: disable=bare-except
            pass
        self._socket.close()

    def timed_out(self) -> "bool|None":
        with self._timed_out_lock:
            if self._timestamp != -1 and _time() - self._timestamp > _Constants.TIMEOUT_INTERVAL:
                print("timed out")
                self.signal_close()
                return True
            return False

    def handle_packet(self, packet: bytes, address: "tuple[str,int]") -> None:
        with self._handle_packet_lock:
            magic_num, version, command, _, session_id = _util.unpack(packet)

            if magic_num == _Constants.MAGIC_NUMBER and version == _Constants.VERSION:
                if session_id != self._server_session_id:
                    self.send_goodbye()
                    self.signal_close()

                if command == _Constants.Command.GOODBYE.value:
                    print("GOODBYE from server.")
                    self.signal_close()
                elif command == _Constants.Command.ALIVE.value and self._sent_data and self._can_send_goodbye:
                    if self._timestamp != -1:
                        self._timestamp = -1
                else:
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
        t = _Thread(target=try_hello_exchange, args=(queue,), daemon=True)
        t.start()

        try:
            command: int = queue.get(timeout=_Constants.TIMEOUT_INTERVAL)
            return command == _Constants.Command.HELLO.value
        except:  # pylint: disable=bare-except
            return False
