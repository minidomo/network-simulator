# pylint: disable=protected-access
# pylint: disable=bare-except
"""Tests for client functionality."""

import time
from queue import Queue
from threading import Thread
from lib.structures import Client
from lib import util
from lib import constants as Constants

_portnum = 1456


def make_client() -> Client:
    client = Client("localhost", _portnum, 2)
    client._server_session_id = 0
    client._waiting_hello = False

    return client


def test_hello():
    client = make_client()

    hello = util.pack(Constants.Command.HELLO.value, 0, 0)
    client.handle_packet(hello, client._server_address)

    assert client._can_send_goodbye is False
    assert client._can_send_data is False
    assert client._signal_queue.qsize() == 1


def test_alive():
    client = make_client()

    client.send_data("data")

    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)
    client.handle_packet(alive, client._server_address)

    assert client._can_send_goodbye is True
    assert client._can_send_data is True
    assert client._signal_queue.qsize() == 0


def test_goodbye():
    client = make_client()

    goodbye = util.pack(Constants.Command.GOODBYE.value, 0, 0)
    client.handle_packet(goodbye, client._server_address)

    assert client._can_send_goodbye is False
    assert client._can_send_data is False
    assert client._signal_queue.qsize() == 1


def test_data():
    client = make_client()

    data = util.pack(Constants.Command.DATA.value, 0, 0)  # ignore actual data since that would get split off
    client.handle_packet(data, client._server_address)

    assert client._can_send_goodbye is False
    assert client._can_send_data is False
    assert client._signal_queue.qsize() == 1


def test_no_timeout():
    client = make_client()

    client.send_data("1")
    client.send_data("2")
    client.send_data("3")
    client.send_data("4")
    client.send_data("5")

    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)
    client.handle_packet(alive, client._server_address)

    time.sleep(client.timeout_interval)

    assert client._timestamp == -1
    assert client.timed_out() is False
    assert client._can_send_goodbye is True
    assert client._can_send_data is True
    assert client._signal_queue.qsize() == 0


def test_data_timeout():
    client = make_client()

    client.send_data("a")

    time.sleep(client.timeout_interval)

    assert client.timed_out() is True
    assert client._can_send_goodbye is False
    assert client._can_send_data is False
    assert client._signal_queue.qsize() == 0


def test_goodbye_timeout():
    client = make_client()

    client.send_goodbye()

    time.sleep(client.timeout_interval)

    assert client.timed_out() is True
    assert client._can_send_goodbye is False
    assert client._can_send_data is False
    assert client._signal_queue.qsize() == 0


def test_seq():
    client = make_client()

    client._send_packet(Constants.Command.HELLO.value)
    client._send_packet(Constants.Command.DATA.value, "1")
    client._send_packet(Constants.Command.DATA.value, "2")
    client._send_packet(Constants.Command.DATA.value, "3")
    client._send_packet(Constants.Command.DATA.value, "4")

    assert client._seq == 5


def test_alive_no_data():
    client = make_client()

    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)
    client.handle_packet(alive, client._server_address)

    assert client._can_send_goodbye is True
    assert client._can_send_data is True
    assert client._signal_queue.qsize() == 0


def test_hello_exchange_timeout():
    client = make_client()

    client.send_hello()

    time.sleep(client.timeout_interval)

    assert client.timed_out() is True
    assert client._can_send_goodbye is False
    assert client._can_send_data is False
    assert client._signal_queue.qsize() == 0


def test_close_timeout_then_packet():
    client = make_client()

    client.send_data("abc")
    time.sleep(client.timeout_interval)
    client.timed_out()
    time.sleep(client.timeout_interval)
    client.timed_out()
    signal = client.wait_for_signal()
    client.close()

    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)
    client.handle_packet(alive, client._server_address)

    assert signal == Constants.Signal.CLOSE
    assert client._can_send_goodbye is False
    assert client._can_send_data is False
    assert client._timestamp != -1


def test_wait_for_close():

    def runnable(queue: Queue, client: Client):
        client.wait_for_signal()
        queue.put(None)

    client = make_client()

    queue = Queue()
    t = Thread(target=runnable, args=(queue, client), daemon=True)
    t.start()

    blocked = False

    try:
        queue.get(timeout=client.timeout_interval * 2)
    except:
        blocked = True

    assert blocked is True


def test_close_then_keyboard():
    client = make_client()

    client.signal_close()
    client.wait_for_signal()
    client.close()

    client.send_data("abc")

    assert client._seq == 0
