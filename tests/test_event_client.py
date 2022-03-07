# pylint: disable=protected-access
# pylint: disable=bare-except
# pylint: disable=unused-argument
"""Tests for event-based client functionality."""

import random
import pyuv
from lib.constants import Command
from lib.structures import EventClient
from lib import util
from lib import constants

_loop = pyuv.Loop.default_loop()


def end_loop() -> None:

    def empty_event():
        pass

    end_loop_async = pyuv.Async(_loop, empty_event)

    _loop.stop()
    end_loop_async.send()


def make_client(stage: str) -> EventClient:
    portnum = random.randint(60000, 64000)
    client = EventClient("localhost", portnum, -1, _loop, end_loop)
    if stage == "hello":
        client._waiting_for_hello = True
    elif stage in ("ready", "closing"):
        client._seq = 1
        client._waiting_for_hello = False
        if stage == "closing":
            client._timer_active = True
            client._seq = 2
            client._can_send_goodbye = False
            client._can_send_data = False
    return client


# tests
class TestHelloExchange:
    """
    Testing hello exchange stage
    """

    def test_bad_address(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            packet = util.pack(Command.HELLO.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=("odfgjhiodfh", client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 1
        assert client._timer_active is True
        assert client._waiting_for_hello is True
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_bad_packet_header(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            packet = util._pack(constants.PACKET_FORMAT, constants.MAGIC_NUMBER + 1, constants.VERSION,
                                Command.HELLO.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 1
        assert client._timer_active is True
        assert client._waiting_for_hello is True
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_small_packet(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            packet = b"osdif"
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 1
        assert client._timer_active is True
        assert client._waiting_for_hello is True
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_good(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            packet = util.pack(Command.HELLO.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 1
        assert client._timer_active is False
        assert client._waiting_for_hello is False
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_bad(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            packet = util.pack(Command.ALIVE.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._waiting_for_hello is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_hello_wrong_session_id(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            packet = util.pack(Command.HELLO.value, 0, client._session_id + 5)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            client.timed_out()

            packet = util.pack(Command.ALIVE.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is True
        assert client._waiting_for_hello is False
        assert client._closed is False
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout_good(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            client.timed_out()

            if not client.is_waiting_for_hello():
                packet = util.pack(Command.GOODBYE.value, 1, client._session_id)
                client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))
            else:
                packet = util.pack(Command.HELLO.value, 0, client._session_id)
                client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._waiting_for_hello is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout_bad(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            client.timed_out()

            if not client.is_waiting_for_hello():
                packet = util.pack(Command.HELLO.value, 1, client._session_id)
                client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))
            else:
                packet = util.pack(Command.HELLO.value, 0, client._session_id)
                client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._waiting_for_hello is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout_ignore(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            client.timed_out()

            if not client.is_waiting_for_hello():
                packet = util.pack(Command.ALIVE.value, 1, client._session_id)
                client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))
            else:
                packet = util.pack(Command.HELLO.value, 0, client._session_id)
                client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is True
        assert client._waiting_for_hello is False
        assert client._closed is False
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_two_timeout(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            client.timed_out()

            if not client.is_waiting_for_hello():
                client.timed_out()
            else:
                packet = util.pack(Command.HELLO.value, 0, client._session_id)
                client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._waiting_for_hello is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_stdin(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()
            if not client.is_waiting_for_hello():
                client.send_data("test")
            else:
                packet = util.pack(Command.HELLO.value, 0, client._session_id)
                client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 1
        assert client._timer_active is False
        assert client._waiting_for_hello is False
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_stdin_q(self):
        client = make_client("hello")

        def runnable(handle=None):

            client.send_hello()

            # eof/q
            client.send_goodbye()

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is True
        assert client._waiting_for_hello is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False


class TestReady:
    """
    Testing ready stage
    """

    def test_pre_ignore(self):
        client = make_client("ready")

        def runnable(handle=None):

            packet = util.pack(Command.ALIVE.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 1
        assert client._timer_active is False
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_pre_goodbye(self):
        client = make_client("ready")

        def runnable(handle=None):

            packet = util.pack(Command.GOODBYE.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 1
        assert client._timer_active is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_pre_bad(self):
        client = make_client("ready")

        def runnable(handle=None):

            packet = util.pack(Command.DATA.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data(self):
        client = make_client("ready")

        def runnable(handle=None):

            client.send_data("test")

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is True
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_send_data_receive_alive(self):
        client = make_client("ready")

        def runnable(handle=None):

            client.send_data("test")
            packet = util.pack(Command.ALIVE.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_send_data_receive_goodbye(self):
        client = make_client("ready")

        def runnable(handle=None):

            client.send_data("test")
            packet = util.pack(Command.GOODBYE.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data_receive_random(self):
        client = make_client("ready")

        def runnable(handle=None):
            client.send_data("test")
            packet = util.pack(Command.DEFAULT.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 3
        assert client._timer_active is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data_timeout(self):
        client = make_client("ready")

        def runnable(handle=None):
            client.send_data("test")
            client.timed_out()

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 3
        assert client._timer_active is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data_bad_session_id(self):
        client = make_client("ready")

        def runnable(handle=None):
            client.send_data("test")
            packet = util.pack(Command.ALIVE.value, 0, client._session_id + 1)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 3
        assert client._timer_active is False
        assert client._closed is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data_twice(self):
        client = make_client("ready")

        def runnable(handle=None):
            client.send_data("test")
            client.send_data("test")

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 3
        assert client._timer_active is True
        assert client._can_send_data is True
        assert client._can_send_goodbye is True


class TestClosing:
    """
    Testing closing stage
    """

    def test_receive_alive(self):
        client = make_client("closing")

        def runnable(handle=None):
            packet = util.pack(Command.ALIVE.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is True

    def test_receive_goodbye(self):
        client = make_client("closing")

        def runnable(handle=None):
            packet = util.pack(Command.GOODBYE.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._closed is True

    def test_receive_random(self):
        client = make_client("closing")

        def runnable(handle=None):
            packet = util.pack(Command.DEFAULT.value, 0, client._session_id)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._closed is True

    def test_timeout(self):
        client = make_client("closing")

        def runnable(handle=None):
            client.timed_out()

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._closed is True

    def test_receive_goodbye_bad_session_id(self):
        client = make_client("closing")

        def runnable(handle=None):
            packet = util.pack(Command.GOODBYE.value, 0, client._session_id + 1)
            client.handle_packet(packet=packet, address=(client._server_ip_address, client._server_port))

            end_loop()

        f = pyuv.Async(_loop, runnable)
        f.send()

        _loop.run()

        assert client._seq == 2
        assert client._timer_active is False
        assert client._closed is True
