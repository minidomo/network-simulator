import socket as _socket
import threading as _threading
from time import time as _time
from .. import util as _util
from .. import constants as _Constants
from . import ClientData as _ClientData
from . import BufferedWriter as _BufferedWriter


class Server:

    def __init__(self, portnum: int, bf: _BufferedWriter) -> None:
        self._socket = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        self._socket.bind((b"0.0.0.0", portnum))
        self._seq = 0
        self._bf = bf
        self._client_data_map: "dict[int, _ClientData]" = {}
        self._map_lock = _threading.Lock()
        self._close_lock = _threading.Lock()
        self.closed = False

    def send_packet(self, address: "tuple[str,int]", command: int, session_id: int, data: str = None) -> None:
        encoded_data = _util.pack(command, self._seq, session_id, data)
        self._socket.sendto(encoded_data, address)
        self._seq += 1

    def _determine_response(self, packet: bytes, address: "tuple[str,int]") -> _Constants.Response:
        if len(packet) < _Constants.HEADER_SIZE:
            return _Constants.Response.IGNORE

        packet_header = packet[:_Constants.HEADER_SIZE]
        magic_num, version, command, seq, session_id = _util.unpack(packet_header)

        if magic_num != _Constants.MAGIC_NUMBER or version != _Constants.VERSION:
            return _Constants.Response.IGNORE

        with self._map_lock:
            client = self._client_data_map.get(session_id, None)
            if client is None:
                if seq == 0:
                    if command == _Constants.Command.HELLO.value:
                        return _Constants.Response.NORMAL
                    else:
                        return _Constants.Response.IGNORE
                else:
                    return _Constants.Response.IGNORE
            else:
                # existing session id but from different address
                if address[0] != client.address[0] or address[1] != client.address[1]:
                    return _Constants.Response.IGNORE

                if seq == client.packet_number:
                    # duplicate packet
                    values = (_Constants.Command.HELLO.value, _Constants.Command.DATA.value,
                              _Constants.Command.GOODBYE.value)
                    if (command in values and command == client.previous_command):
                        self._client_log(session_id, "Duplicate packet!", seq)
                        return _Constants.Response.IGNORE
                    else:
                        return _Constants.Response.CLOSE
                elif seq < client.packet_number:
                    # out of order delivery (could also be wrap around but will not be tested on it)
                    return _Constants.Response.CLOSE
                else:
                    if seq > client.packet_number + 1:
                        for i in range(client.packet_number + 1, seq):
                            self._client_log(session_id, "Lost packet!", i)
                    if command == _Constants.Command.HELLO.value:
                        return _Constants.Response.CLOSE
                    elif command == _Constants.Command.ALIVE.value:
                        return _Constants.Response.CLOSE
                    elif command == _Constants.Command.GOODBYE.value:
                        return _Constants.Response.NORMAL
                    elif command == _Constants.Command.DATA.value:
                        return _Constants.Response.NORMAL
                    else:
                        return _Constants.Response.CLOSE

    def handle_packet(self, packet: bytes, address: "tuple[str,int]") -> "_Constants.Command|None":
        with self._close_lock:
            response = self._determine_response(packet, address)

            ret_command: "_Constants.Command|None" = None

            if response == _Constants.Response.NORMAL:
                packet_header = packet[:_Constants.HEADER_SIZE]
                _, _, command, seq, session_id = _util.unpack(packet_header)

                with self._map_lock:
                    if session_id in self._client_data_map:
                        client = self._client_data_map[session_id]
                        client.packet_number = seq
                        client.previous_command = command

                if command == _Constants.Command.HELLO.value:
                    with self._map_lock:
                        ret_command = _Constants.Command.HELLO
                        self.send_packet(address, command, session_id)
                        self._client_log(session_id, "Session created", seq)

                        client = _ClientData(session_id, address)
                        client.timestamp = _time()
                        client.packet_number = seq
                        client.previous_command = command
                        self._client_data_map[session_id] = client

                elif command == _Constants.Command.DATA.value:
                    data = packet[_Constants.HEADER_SIZE:].decode("utf-8", "replace").rstrip()

                    with self._map_lock:
                        if session_id in self._client_data_map:
                            ret_command = _Constants.Command.ALIVE
                            client = self._client_data_map[session_id]
                            self.send_packet(address, _Constants.Command.ALIVE.value, session_id)
                            self._client_log(session_id, data, seq)
                            client.timestamp = _time()

                elif command == _Constants.Command.GOODBYE.value:
                    with self._map_lock:
                        if session_id in self._client_data_map:
                            ret_command = _Constants.Command.GOODBYE
                            client = self._client_data_map[session_id]
                            self._client_close(client, True)

                else:
                    raise Exception("Unknown command")

            elif response == _Constants.Response.CLOSE:
                packet_header = packet[:_Constants.HEADER_SIZE]
                _, _, _, _, session_id = _util.unpack(packet_header)

                with self._map_lock:
                    if session_id in self._client_data_map:
                        ret_command = _Constants.Command.GOODBYE
                        client = self._client_data_map[session_id]
                        self._client_close(client, False)

            elif response == _Constants.Response.IGNORE:
                pass
            else:
                raise Exception("Unknown response")

            return ret_command

    def _client_log(self, session_id: int, s: str, seq: "int|None" = None) -> None:
        if seq is None:
            self._bf.write(f"0x{session_id:08x} {s}")
        else:
            self._bf.write(f"0x{session_id:08x} [{seq}] {s}")

    def _client_close(self, client: _ClientData, from_client: bool) -> None:
        del self._client_data_map[client.session_id]

        self.send_packet(client.address, _Constants.Command.GOODBYE.value, client.session_id)
        if from_client:
            self._client_log(client.session_id, "GOODBYE from client.", client.packet_number)
        self._client_log(client.session_id, "Session Closed")

    def prune_inactive_clients(self) -> None:
        for session_id in list(self._client_data_map.keys()):
            with self._map_lock:
                if session_id in self._client_data_map:
                    client = self._client_data_map[session_id]
                    if client.timestamp != -1 and _time() - client.timestamp > _Constants.TIMEOUT_INTERVAL:
                        self._client_close(client, False)

    def close(self) -> None:
        self.closed = True
        self._close_lock.acquire()  # pylint: disable=consider-using-with
        with self._map_lock:
            for client in list(self._client_data_map.values()):
                self._client_close(client, False)
        try:
            self._socket.shutdown(_socket.SHUT_RDWR)
        except:  # pylint: disable=bare-except
            pass
        self._socket.close()

    def receive_packet(self) -> "tuple[bytes,tuple[str,int]]|None":
        return self._socket.recvfrom(_Constants.BUFFER_SIZE)
