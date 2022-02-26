#!/usr/bin/env python3

import socket
import random
import time
from threading import Thread, RLock
from queue import Queue
from .. import constants as Constants
from .. import util


class Client:

    def __init__(self, hostname: str, portnum: int) -> None:
        self._session_id = random.randint(0, 2**32)
        self._seq = 0
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._server_address = (hostname, portnum)
        self._close_lock = RLock()
        self._keyboard_lock = RLock()
        self._socket_lock = RLock()
        self._client_closing = False
        self._waiting_message_time = -1
        self.sent_data = False

    def __del__(self):
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        self._socket.close()

    def send_packet(self, command: int, data: str = None):
        data_msg = util.pack(command, self._seq, self._session_id, data)
        self._socket.sendto(data_msg, self._server_address)
        self._seq += 1

    def close_client(self, send: bool):
        with self._close_lock:  # two threads might try to close at the same time
            if not self._client_closing:
                if send:
                    self._waiting_message_time = time.time()
                    self.send_packet(Constants.Command.GOODBYE.value)
                self._client_closing = True
                self._keyboard_lock.acquire()  # prevent any further keyboard input from being processed

    # Returns whether the client timed out
    def timeout(self) -> bool:
        if self._waiting_message_time != -1 and time.time() - self._waiting_message_time > Constants.TIMEOUT_INTERVAL:
            if not self._client_closing:
                print("Timeout")
                # Let the socket finish a packet it is currently processing, then prevent it from processing any more
                self._socket_lock.acquire()
                self.close_client(False)
            return True
        return False

    def send_data(self, text: str):
        with self._keyboard_lock:
            if self._waiting_message_time == -1:  # Set the timeout for the first packet after the timer was cancelled
                self._waiting_message_time = time.time()
            self.sent_data = True
            self.send_packet(Constants.Command.DATA.value, text)

    def receive_packet(self):
        packet, _ = self._socket.recvfrom(Constants.BUFFER_SIZE)
        return packet

    # Returns whether the client is closing
    def handle_packet(self, packet):

        def log(session_id: int, seq: "int | None", msg: str):
            if seq is None:
                print(f"0x{session_id:08x} {msg}")
            else:
                print(f"0x{session_id:08x} [{seq}] {msg}")

        with self._socket_lock:
            magic_num, version, command, seq, session_id = util.unpack(packet)

            if magic_num == Constants.MAGIC_NUMBER and version == Constants.VERSION:
                if command == Constants.Command.GOODBYE.value:
                    log(session_id, seq, "GOODBYE from server.")
                    self.close_client(False)
                    return False
                elif command == Constants.Command.ALIVE.value and self.sent_data:
                    if self._waiting_message_time != -1:
                        self._waiting_message_time = -1
                else:
                    print(f"Invalid command: {command}")
                    self.close_client(True)
                    return False

        return True

    def hello_exchange(self):
        # stop and wait
        def try_hello_exchange(result_queue: Queue):
            self.send_packet(Constants.Command.HELLO.value)
            while True:
                packet, _ = self._socket.recvfrom(Constants.BUFFER_SIZE)
                magic_num, version, command, _, _ = util.unpack(packet)
                if magic_num == Constants.MAGIC_NUMBER and version == Constants.VERSION:
                    result_queue.put(command)
                    break

        queue = Queue()
        t = Thread(target=try_hello_exchange, args=(queue,), daemon=True)
        t.start()

        try:
            command: int = queue.get(block=True, timeout=Constants.TIMEOUT_INTERVAL)
            return command == Constants.Command.HELLO.value
        except Exception as _:
            return False
