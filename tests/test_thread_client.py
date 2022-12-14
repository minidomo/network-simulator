# pylint: disable=protected-access
# pylint: disable=bare-except
"""Tests for thread-based client functionality."""

import time
import random
from lib.constants import Command
from lib.structures import ThreadClient
from lib import util
from lib import constants


def make_client(stage: str) -> ThreadClient:
    portnum = random.randint(60000, 64000)
    client = ThreadClient("localhost", portnum, 1)
    if stage == "hello":
        client._waiting_for_hello = True
    else:
        client._seq = 1
        client._waiting_for_hello = False
        if stage == "ready":
            pass
        else:
            client._timestamp = time.time()
            client._timer_active = True
            client._seq = 2
            client._can_send_goodbye = False
            client._can_send_data = False
            if stage == "closing":
                pass
            elif stage == "closed":
                client.close()

    return client


# tests
class TestHelloExchange:
    """
    Testing hello exchange stage
    """

    def test_bad_address(self):
        client = make_client("hello")

        client.send_hello()
        if not client.timed_out():
            packet = util.pack(Command.HELLO.value, 0, client._session_id)
            client.handle_packet(packet, ("odfgjhiodfh", client._server_port))

        assert client._seq == 1
        assert client._timestamp != -1
        assert client._waiting_for_hello is True
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_bad_packet_header(self):
        client = make_client("hello")

        client.send_hello()
        if not client.timed_out():
            packet = util._pack(constants.PACKET_FORMAT, constants.MAGIC_NUMBER + 1, constants.VERSION,
                                Command.HELLO.value, 0, client._session_id)
            client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 1
        assert client._timestamp != -1
        assert client._waiting_for_hello is True
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_small_packet(self):
        client = make_client("hello")

        client.send_hello()
        if not client.timed_out():
            packet = b"osdif"
            client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 1
        assert client._timestamp != -1
        assert client._waiting_for_hello is True
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_good(self):
        client = make_client("hello")

        client.send_hello()
        if not client.timed_out():
            packet = util.pack(Command.HELLO.value, 0, client._session_id)
            client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 1
        assert client._timestamp == -1
        assert client._waiting_for_hello is False
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_bad(self):
        client = make_client("hello")

        client.send_hello()
        if not client.timed_out():
            packet = util.pack(Command.ALIVE.value, 0, client._session_id)
            client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._waiting_for_hello is False
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_hello_wrong_session_id(self):
        client = make_client("hello")

        client.send_hello()
        if not client.timed_out():
            packet = util.pack(Command.HELLO.value, 0, client._session_id + 5)
            client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout(self):
        client = make_client("hello")

        client.send_hello()
        time.sleep(client.timeout_interval)

        assert client.timed_out()

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._waiting_for_hello is False
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout_good(self):
        client = make_client("hello")

        client.send_hello()
        time.sleep(client.timeout_interval)

        assert client.timed_out()

        packet = util.pack(Command.GOODBYE.value, 1, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client.timed_out() is False

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._waiting_for_hello is False
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout_bad(self):
        client = make_client("hello")

        client.send_hello()
        time.sleep(client.timeout_interval)

        assert client.timed_out()

        packet = util.pack(Command.HELLO.value, 1, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._waiting_for_hello is False
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout_ignore(self):
        client = make_client("hello")

        client.send_hello()
        time.sleep(client.timeout_interval)

        assert client.timed_out()

        packet = util.pack(Command.ALIVE.value, 1, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._waiting_for_hello is False
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_one_timeout_reset_timer(self):
        client = make_client("hello")

        client.send_hello()
        time.sleep(client.timeout_interval)

        assert client.timed_out()

        packet = util.pack(Command.ALIVE.value, 1, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        time.sleep(2)

        packet = util.pack(Command.ALIVE.value, 1, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        time.sleep(4)

        assert client.timed_out()

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._waiting_for_hello is False
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_two_timeout(self):
        client = make_client("hello")

        client.send_hello()
        time.sleep(client.timeout_interval)

        assert client.timed_out()

        time.sleep(client.timeout_interval)

        assert client.timed_out()

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._waiting_for_hello is False
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_stdin(self):
        client = make_client("hello")

        client.send_hello()

        timestamp = client._timestamp

        client.send_data("test")

        assert client._seq == 1
        assert client._timestamp == timestamp
        assert client._waiting_for_hello is True
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_stdin_q(self):
        client = make_client("hello")

        client.send_hello()

        client.send_goodbye()

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._waiting_for_hello is True
        assert client._can_send_data is False
        assert client._can_send_goodbye is False


class TestReady:
    """
    Testing ready stage
    """

    def test_pre_ignore(self):
        client = make_client("ready")

        packet = util.pack(Command.ALIVE.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 1
        assert client._timestamp == -1
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_pre_goodbye(self):
        client = make_client("ready")

        packet = util.pack(Command.GOODBYE.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 1
        assert client._timestamp == -1
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_pre_bad(self):
        client = make_client("ready")

        packet = util.pack(Command.DATA.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data(self):
        client = make_client("ready")

        client.send_data("test")

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_send_data_receive_alive(self):
        client = make_client("ready")

        client.send_data("test")
        packet = util.pack(Command.ALIVE.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp == -1
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True

    def test_send_data_receive_goodbye(self):
        client = make_client("ready")

        client.send_data("test")
        packet = util.pack(Command.GOODBYE.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data_receive_random(self):
        client = make_client("ready")

        client.send_data("test")
        packet = util.pack(Command.DEFAULT.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 3
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data_timeout(self):
        client = make_client("ready")

        client.send_data("test")
        time.sleep(client.timeout_interval)
        client.timed_out()

        assert client._seq == 3
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data_bad_session_id(self):
        client = make_client("ready")

        client.send_data("test")
        packet = util.pack(Command.ALIVE.value, 0, client._session_id + 1)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 3
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1
        assert client._can_send_data is False
        assert client._can_send_goodbye is False

    def test_send_data_twice_timestamp(self):
        client = make_client("ready")

        client.send_data("test")
        f_timestamp = client._timestamp
        client.send_data("test")

        assert client._seq == 3
        assert client._timestamp == f_timestamp
        assert client._signal_queue.qsize() == 0
        assert client._can_send_data is True
        assert client._can_send_goodbye is True


class TestClosing:
    """
    Testing closing stage
    """

    def test_receive_alive(self):
        client = make_client("closing")

        packet = util.pack(Command.ALIVE.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 0

    def test_receive_goodbye(self):
        client = make_client("closing")

        packet = util.pack(Command.GOODBYE.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1

    def test_receive_random(self):
        client = make_client("closing")

        packet = util.pack(Command.DEFAULT.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1

    def test_timeout(self):
        client = make_client("closing")

        time.sleep(client.timeout_interval)
        client.timed_out()

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1

    def test_receive_goodbye_bad_session_id(self):
        client = make_client("closing")

        packet = util.pack(Command.GOODBYE.value, 0, client._session_id + 1)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._seq == 2
        assert client._timestamp != -1
        assert client._signal_queue.qsize() == 1


class TestClosed:
    """
    Testing closed stage
    """

    def test_timeout(self):
        client = make_client("closed")

        time.sleep(client.timeout_interval)
        ret_val = client.timed_out()

        assert ret_val is None
        assert client._signal_queue.qsize() == 0

    def test_send_data(self):
        client = make_client("closed")

        client.send_data("test")

        assert client._seq == 2

    def test_receive_goodbye(self):
        client = make_client("closed")

        packet = util.pack(Command.GOODBYE.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._signal_queue.qsize() == 0

    def test_receive_alive(self):
        client = make_client("closed")

        packet = util.pack(Command.ALIVE.value, 0, client._session_id)
        client.handle_packet(packet, (client._server_ip_address, client._server_port))

        assert client._signal_queue.qsize() == 0
