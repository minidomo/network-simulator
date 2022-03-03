"""A thread-based server."""

import socket as _socket
import threading as _threading
from time import time as _time
from .. import util as _util
from .. import constants as _Constants
from . import ClientData as _ClientData
from . import BufferedWriter as _BufferedWriter


class Server:
    """
    A thread-based server.
    """

    def __init__(self, portnum: int, bf: _BufferedWriter, timeout_interval: int) -> None:
        """
        Creates a thread-based server with a given port number, buffered writer, timeout_interval.

        Parameters
        ----------
        portnum : int
            The port number for the server to listen to.
        bf : BufferedWriter
            The buffered writer to use.
        timeout_interval : int
            The maximum amount of time for timeout.
        """
        self._socket = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        self._socket.bind((b"0.0.0.0", portnum))
        self._seq = 0
        self._bf = bf
        self.timeout_interval = timeout_interval

        self._client_data_map: "dict[int, _ClientData]" = {}
        self._map_lock = _threading.Lock()

        self._closed = False
        self._closed_lock = _threading.Lock()

    def closed(self) -> bool:
        with self._closed_lock:
            return self._closed

    def send_packet(self, address: "tuple[str,int]", command: int, session_id: int, data: "str|None" = None) -> None:
        """
        Sends a packet to a given address.

        The sequence number of the server will also increment by one.

        Parameters
        ----------
        address : tuple[str,int]
            The address of the client.
        command : int
            The command number.
        session_id : int
            The session id of the client.
        data : str | None
            The data to send with the packet. Default value is None.
        """
        encoded_data = _util.pack(command, self._seq, session_id, data)
        self._socket.sendto(encoded_data, address)
        self._seq += 1

    def _determine_response(self, packet: bytes, address: "tuple[str,int]") -> _Constants.Response:
        """
        Determines the response for the server to take given a packet and address.

        Parameters
        ----------
        packet : bytes
            The packet.
        address : tuple[str,int]
            The address of where the packet originated from.

        Returns
        -------
        Response
            The server's response to the packet and address.
        """
        # not a P0P packet
        if len(packet) < _Constants.HEADER_SIZE:
            return _Constants.Response.IGNORE

        packet_header = packet[:_Constants.HEADER_SIZE]
        magic_num, version, command, seq, session_id = _util.unpack(packet_header)

        # not a P0P packet
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

                if seq == client.prev_packet_num:
                    # duplicate packet
                    values = (_Constants.Command.HELLO.value, _Constants.Command.DATA.value,
                              _Constants.Command.GOODBYE.value)
                    if (command in values and command == client.prev_command_num):
                        self._client_log(session_id, "Duplicate packet!", seq)
                        return _Constants.Response.IGNORE
                    else:
                        return _Constants.Response.CLOSE
                elif seq < client.prev_packet_num:
                    # out of order delivery (could also be wrap around but will not be tested on it)
                    return _Constants.Response.CLOSE
                else:
                    if seq > client.prev_packet_num + 1:
                        for i in range(client.prev_packet_num + 1, seq):
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
        """
        Process a packet if the server is not closed.

        Parameters
        ----------
        packet : bytes
            The packet.
        address : tuple[str,int]
            The address from where the packet originated.

        Returns
        -------
        Command | None
            The command that was sent back to the given address. None if nothing was sent.
        """
        ret_command: "_Constants.Command|None" = None

        if not self.closed():
            response = self._determine_response(packet, address)

            if response == _Constants.Response.NORMAL:
                packet_header = packet[:_Constants.HEADER_SIZE]
                _, _, command, seq, session_id = _util.unpack(packet_header)

                with self._map_lock:
                    if session_id in self._client_data_map:
                        # update the sequence number and command number
                        client = self._client_data_map[session_id]
                        client.prev_packet_num = seq
                        client.prev_command_num = command

                if command == _Constants.Command.HELLO.value:
                    ret_command = _Constants.Command.HELLO
                    self.send_packet(address, command, session_id)
                    self._client_log(session_id, "Session created", seq)

                    with self._map_lock:
                        client = _ClientData(session_id, address)
                        client.timestamp = _time()
                        client.prev_packet_num = seq
                        client.prev_command_num = command
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
        """
        Logs client data to the buffered writer.

        Parameters
        ----------
        session_id : int
            The session id.
        s : str
            The string to log.
        seq : int | None
            The sequence number to use.
        """
        if seq is None:
            self._bf.write(f"0x{session_id:08x} {s}")
        else:
            self._bf.write(f"0x{session_id:08x} [{seq}] {s}")

    def _client_close(self, client: _ClientData, from_client: bool) -> None:
        """
        Closes the given client.

        Parameters
        ----------
        client : ClientData
            The client.
        from_client : bool
            Indicate whether the source of the close was from the client.
        """
        del self._client_data_map[client.session_id]

        self.send_packet(client.address, _Constants.Command.GOODBYE.value, client.session_id)
        if from_client:
            self._client_log(client.session_id, "GOODBYE from client.", client.prev_packet_num)
        self._client_log(client.session_id, "Session Closed")

    def prune_inactive_clients(self) -> None:
        """
        Remove clients that have not communicated with the server within the timeout interval.
        """
        for session_id in list(self._client_data_map.keys()):
            with self._map_lock:
                if session_id in self._client_data_map:
                    client = self._client_data_map[session_id]
                    if client.timestamp != -1 and _time() - client.timestamp > self.timeout_interval:
                        self._client_close(client, False)

    def close(self) -> None:
        """
        Closes the server.

        Sends goodbye to all current clients and shutdowns and closes the server's socket.
        """
        with self._closed_lock:
            self._closed = True

        with self._map_lock:
            for client in list(self._client_data_map.values()):
                self._client_close(client, False)
        try:
            self._socket.shutdown(_socket.SHUT_RDWR)
        except:  # pylint: disable=bare-except
            pass
        self._socket.close()

    def receive_packet(self) -> "tuple[bytes,tuple[str,int]]":
        """
        Returns a packet that was sent to the client.

        Will block the calling thread until a packet is received or server's socket is shutdown.

        Returns
        -------
        tuple[bytes,tuple[str,int]]
            The packet that was sent to the server.
        """
        return self._socket.recvfrom(_Constants.BUFFER_SIZE)
