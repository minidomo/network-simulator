# pylint: disable=protected-access

import random
from lib.structures import Server, BufferedWriter, ClientData
from lib import constants as Constants
from lib import util


def make_server() -> Server:
    portnum = random.randint(60000, 64000)
    bf = BufferedWriter(None, "w", 5000000, "utf-8")
    server = Server(portnum, bf)

    return server


_server = make_server()


def reset_server(server: Server):
    server._client_data_map.clear()
    queue = server._bf._queue
    size = queue.qsize()
    for _ in range(size):
        queue.get()


def make_address(hostname: str = None, portnum: int = None) -> "tuple[str,int]":
    f_hostname = hostname
    if f_hostname is None:
        f_hostname = f"""{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(
            0, 255)}.{random.randint(0, 255)}"""
    f_portnum = portnum
    if f_portnum is None:
        f_portnum = random.randint(30000, 60000)
    return (f_hostname, f_portnum)


def make_client_data(seq_prev: int, command_prev: int) -> ClientData:
    session_id = random.randint(0, 2**16)
    address = make_address()
    client = ClientData(session_id, address)
    client.packet_number = seq_prev
    client.previous_command = command_prev
    return client


# test functions

# testing the server response


def test_response_small_packet():
    reset_server(_server)
    packet = b"sodkf"
    address = make_address()

    res = _server._determine_response(packet, address)

    assert res == Constants.Response.IGNORE


def test_response_mismatched_magic():
    reset_server(_server)
    packet = util._pack(Constants.PACKET_FORMAT, 234, Constants.VERSION, Constants.Command.HELLO.value, 0, 0)
    address = make_address()

    res = _server._determine_response(packet, address)

    assert res == Constants.Response.IGNORE


def test_response_mismatched_version():
    reset_server(_server)
    packet = util._pack(Constants.PACKET_FORMAT, Constants.MAGIC_NUMBER, 2, Constants.Command.HELLO.value, 0, 0)
    address = make_address()

    res = _server._determine_response(packet, address)

    assert res == Constants.Response.IGNORE


def test_response_unexpected_packet_seq():
    reset_server(_server)
    packet = util.pack(Constants.Command.HELLO.value, 1, 0)
    address = make_address()

    res = _server._determine_response(packet, address)

    assert res == Constants.Response.IGNORE


def test_response_unexpected_packet_command():
    reset_server(_server)
    packet = util.pack(Constants.Command.DATA.value, 0, 0)
    address = make_address()

    res = _server._determine_response(packet, address)

    assert res == Constants.Response.IGNORE


def test_response_first_hello():
    reset_server(_server)
    packet = util.pack(Constants.Command.HELLO.value, 0, 0)
    address = make_address()

    res = _server._determine_response(packet, address)

    assert res == Constants.Response.NORMAL


def test_response_same_sid_different_hostname():
    reset_server(_server)
    client = make_client_data(0, Constants.Command.HELLO.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number + 1, client.session_id, "a")
    address = make_address(portnum=client.address[1])

    res = _server._determine_response(packet, address)

    assert res == Constants.Response.IGNORE


def test_response_same_sid_different_address():
    reset_server(_server)
    client = make_client_data(0, Constants.Command.HELLO.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number + 1, client.session_id, "a")
    address = make_address(hostname=client.address[0])

    res = _server._determine_response(packet, address)

    assert res == Constants.Response.IGNORE


def test_response_duplicate_packet_different_command():
    reset_server(_server)
    client = make_client_data(0, Constants.Command.HELLO.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number, client.session_id, "a")

    res = _server._determine_response(packet, client.address)

    assert res == Constants.Response.CLOSE


def test_response_duplicate_packet_same_command():
    reset_server(_server)
    client = make_client_data(0, Constants.Command.HELLO.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.HELLO.value, client.packet_number, client.session_id)

    res = _server._determine_response(packet, client.address)
    sout: str = _server._bf._queue.get()

    assert res == Constants.Response.IGNORE
    assert sout.endswith("Duplicate packet!")


def test_response_out_of_order_delivery():
    reset_server(_server)
    client = make_client_data(2, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number - 1, client.session_id)

    res = _server._determine_response(packet, client.address)

    assert res == Constants.Response.CLOSE


def test_response_lost_packets():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number + 5, client.session_id, "a")

    res = _server._determine_response(packet, client.address)

    size = _server._bf._queue.qsize()
    all_lost = True
    for _ in range(size):
        sout: str = _server._bf._queue.get()
        all_lost &= sout.endswith("Lost packet!")

    assert res == Constants.Response.NORMAL
    assert all_lost


def test_response_receive_another_hello():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.HELLO.value, client.packet_number + 1, client.session_id)

    res = _server._determine_response(packet, client.address)

    assert res == Constants.Response.CLOSE


def test_response_receive_alive():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.ALIVE.value, client.packet_number + 1, client.session_id)

    res = _server._determine_response(packet, client.address)

    assert res == Constants.Response.CLOSE


def test_response_receive_goodbye():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.GOODBYE.value, client.packet_number + 1, client.session_id)

    res = _server._determine_response(packet, client.address)

    assert res == Constants.Response.NORMAL


def test_response_receive_data():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number + 1, client.session_id, "a")

    res = _server._determine_response(packet, client.address)

    assert res == Constants.Response.NORMAL


def test_response_receive_unknown_command():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DEFAULT.value, client.packet_number + 1, client.session_id, "a")

    res = _server._determine_response(packet, client.address)

    assert res == Constants.Response.CLOSE


# testing server packet handling


def test_handle_first_hello():
    reset_server(_server)
    seq = 0
    session_id = 0
    packet = util.pack(Constants.Command.HELLO.value, seq, session_id)
    address = make_address()

    res = _server.handle_packet(packet, address)

    sout: str = _server._bf._queue.get()

    assert res == Constants.Command.HELLO
    assert sout.endswith("Session created")
    assert session_id in _server._client_data_map


def test_handle_duplicate_packet_different_command():
    reset_server(_server)
    client = make_client_data(0, Constants.Command.HELLO.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number, client.session_id, "a")

    res = _server.handle_packet(packet, client.address)

    sout: str = _server._bf._queue.get()

    assert res == Constants.Command.GOODBYE
    assert client.session_id not in _server._client_data_map
    assert sout.endswith("Session Closed")


def test_handle_out_of_order_delivery():
    reset_server(_server)
    client = make_client_data(2, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number - 1, client.session_id)

    res = _server.handle_packet(packet, client.address)

    sout: str = _server._bf._queue.get()

    assert res == Constants.Command.GOODBYE
    assert client.session_id not in _server._client_data_map
    assert sout.endswith("Session Closed")


def test_handle_receive_another_hello():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.HELLO.value, client.packet_number + 1, client.session_id)

    res = _server.handle_packet(packet, client.address)

    sout: str = _server._bf._queue.get()

    assert res == Constants.Command.GOODBYE
    assert client.session_id not in _server._client_data_map
    assert sout.endswith("Session Closed")


def test_handle_receive_alive():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.ALIVE.value, client.packet_number + 1, client.session_id)

    res = _server.handle_packet(packet, client.address)

    sout: str = _server._bf._queue.get()

    assert res == Constants.Command.GOODBYE
    assert client.session_id not in _server._client_data_map
    assert sout.endswith("Session Closed")


def test_handle_receive_goodbye():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.GOODBYE.value, client.packet_number + 1, client.session_id)

    res = _server.handle_packet(packet, client.address)

    sout1: str = _server._bf._queue.get()
    sout2: str = _server._bf._queue.get()

    assert res == Constants.Command.GOODBYE
    assert sout1.endswith("GOODBYE from client.")
    assert sout2.endswith("Session Closed")
    assert client.session_id not in _server._client_data_map


def test_handle_receive_data():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DATA.value, client.packet_number + 1, client.session_id, "something here")

    res = _server.handle_packet(packet, client.address)

    sout: str = _server._bf._queue.get()

    assert res == Constants.Command.ALIVE
    assert sout.endswith("something here")


def test_handle_receive_unknown_command():
    reset_server(_server)
    client = make_client_data(1, Constants.Command.DATA.value)
    _server._client_data_map[client.session_id] = client

    packet = util.pack(Constants.Command.DEFAULT.value, client.packet_number + 1, client.session_id, "a")

    res = _server.handle_packet(packet, client.address)

    sout: str = _server._bf._queue.get()

    assert res == Constants.Command.GOODBYE
    assert sout.endswith("Session Closed")
    assert client.session_id not in _server._client_data_map