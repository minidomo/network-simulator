# pylint: disable=protected-access

import setup_path  # pylint: disable=unused-import
import time
from threading import Thread
from lib.structures import Client
from lib import util
from lib import constants as Constants

_portnum = 1456


def make_client() -> Client:
    client = Client("localhost", _portnum)

    return client


def test_hello():
    client = make_client()

    hello = util.pack(Constants.Command.HELLO.value, 0, 0)

    assert not client.handle_packet(hello)
    assert client._client_closing


def test_alive():
    client = make_client()

    client.send_data("data")
    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)

    assert client.handle_packet(alive)
    assert not client._client_closing


def test_goodbye():
    client = make_client()

    goodbye = util.pack(Constants.Command.GOODBYE.value, 0, 0)

    assert not client.handle_packet(goodbye)
    assert client._client_closing


def test_data():
    client = make_client()

    data = util.pack(Constants.Command.DATA.value, 0, 0)  # ignore actual data since that would get split off

    assert not client.handle_packet(data)
    assert client._client_closing


def test_exit_timeout():
    client = make_client()

    client.close_client(True)

    time.sleep(Constants.TIMEOUT_INTERVAL)

    assert client.timeout()
    assert client._client_closing


def test_no_timeout():
    client = make_client()

    client.send_data("1")
    client.send_data("2")
    client.send_data("3")
    client.send_data("4")
    client.send_data("5")

    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)

    client.handle_packet(alive)

    time.sleep(Constants.TIMEOUT_INTERVAL)

    assert not client.timeout()
    assert not client._client_closing


def test_data_timeout():
    client = make_client()

    client.send_data("a")

    time.sleep(Constants.TIMEOUT_INTERVAL)

    assert client.timeout()
    assert client._client_closing


def test_goodbye_timeout():
    client = make_client()

    client.close_client(True)

    time.sleep(Constants.TIMEOUT_INTERVAL)

    assert client.timeout()
    assert client._client_closing


def test_seq():
    client = make_client()

    client.send_packet(Constants.Command.HELLO.value)
    client.send_packet(Constants.Command.DATA.value, "1")
    client.send_packet(Constants.Command.DATA.value, "2")
    client.send_packet(Constants.Command.DATA.value, "3")
    client.send_packet(Constants.Command.DATA.value, "4")

    assert client._seq == 5


def test_alive_no_data():
    client = make_client()

    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)

    assert not client.handle_packet(alive)
    assert client._client_closing


def test_hello_exchange_timeout():
    client = make_client()

    client.hello_exchange()

    assert True


def test_close_timeout_then_packet():
    client = make_client()

    client.send_data("abc")

    time.sleep(Constants.TIMEOUT_INTERVAL)

    client.timeout()

    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)

    t1 = Thread(target=client.handle_packet, args=(alive), daemon=True)
    t1.start()
    t1.join(timeout=6)

    assert t1.is_alive()


def test_close_then_packet():
    client = make_client()

    client.close_client(False)

    alive = util.pack(Constants.Command.ALIVE.value, 0, 0)

    t1 = Thread(target=client.handle_packet, args=(alive), daemon=True)
    t1.start()
    t1.join(timeout=6)

    assert t1.is_alive()


def test_close_then_keyboard():
    client = make_client()

    client.close_client(False)

    t1 = Thread(target=client.send_data, args=("abc"), daemon=True)
    t1.start()
    t1.join(timeout=6)

    assert t1.is_alive()
