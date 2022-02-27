#!/usr/bin/env python3

import socket as _socket
import random as _random
from queue import Queue as _Queue
from time import time as _time
from threading import Thread as _Thread, Semaphore as _Semaphore
from .. import constants as _Constants
from .. import util as _util


class Client:

    def __init__(self, hostname: str, portnum: int) -> None:
        self._session_id = _random.randint(0, 2**32)
        self._seq = 0
        self._socket = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        self._server_address = (hostname, portnum)
        self._timestamp = -1
        self._close_queue = _Queue()
        self._close_sema = _Semaphore(2)
        self.closed = False

    def wait_for_close_signal(self):
        self._close_queue.get()

    def signal_close(self):
        self._close_queue.put(None)

    def send_packet(self, command: int, data: str = None) -> None:
        encoded_data = _util.pack(command, self._seq, self._session_id, data)
        self._socket.sendto(encoded_data, self._server_address)
        self._seq += 1

    def send_data(self, text: str) -> None:
        if self._timestamp == -1:
            self._timestamp = _time()
        self.send_packet(_Constants.Command.DATA.value, text)

    def send_goodbye(self) -> None:
        self.send_packet(_Constants.Command.GOODBYE.value)
        self._timestamp = _time()

    def receive_packet(self) -> "tuple[bytes,tuple[str,int]]":
        return self._socket.recvfrom(_Constants.BUFFER_SIZE)

    def close(self) -> None:
        self.closed = True
        self._close_sema.acquire()
        self._close_sema.acquire()
        try:
            self._socket.shutdown(_socket.SHUT_RDWR)
        except:
            pass
        self._socket.close()

    def check_timeout(self) -> None:
        with self._close_sema:
            if self._timestamp != -1 and _time() - self._timestamp > _Constants.TIMEOUT_INTERVAL:
                print("timed out")
                self.signal_close()

    def handle_packet(self, packet: bytes, address: "tuple[str,int]") -> None:
        with self._close_sema:
            magic_num, version, command, _, session_id = _util.unpack(packet)

            if magic_num == _Constants.MAGIC_NUMBER and version == _Constants.VERSION:
                if command == _Constants.Command.GOODBYE.value:
                    print("GOODBYE from server.")
                    self.signal_close()
                elif command == _Constants.Command.ALIVE.value and self._seq > 1:
                    if self._timestamp != -1:
                        self._timestamp = -1
                else:
                    print(f"Invalid command: {command}")
                    self.send_goodbye()
                    self.signal_close()

    def hello_exchange(self) -> bool:
        # stop and wait
        def try_hello_exchange(result_queue: _Queue):
            self.send_packet(_Constants.Command.HELLO.value)
            while True:
                packet, _ = self._socket.recvfrom(_Constants.BUFFER_SIZE)
                magic_num, version, command, _, _ = _util.unpack(packet)
                if magic_num == _Constants.MAGIC_NUMBER and version == _Constants.VERSION:
                    result_queue.put(command)
                    break

        queue = _Queue()
        t = _Thread(target=try_hello_exchange, args=(queue,), daemon=True)
        t.start()

        try:
            command: int = queue.get(timeout=_Constants.TIMEOUT_INTERVAL)
            return command == _Constants.Command.HELLO.value
        except:
            return False
