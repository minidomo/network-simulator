"""Utility methods for P0P."""

import struct
from socket import gethostbyaddr
from . import constants


def _pack(packet_format: str,
          magic: int,
          version: int,
          command: int,
          seq: int,
          session_id: int,
          data: "str|None" = None) -> bytes:
    """
    Create a packet with a given format, magic number, verison number, command, sequence number, session id, and data.

    Parameters
    ----------
    packet_format : str
        The format to use for packing.
    magic : int
        The magic number.
    version : int
        The version number.
    command : int
        The command number.
    seq : int
        The sequence number.
    session_id : int
        The session id.
    data : str | None
        The data to send with this packet. Default value is None.

    Returns
    -------
    bytes
        The packet.
    """
    header = struct.pack(packet_format, magic, version, command, seq, session_id)
    if data is None:
        return header
    return header + data.encode("utf-8", "replace")


def pack(command: int, seq: int, session_id: int, data: "str|None" = None) -> bytes:
    """
    Create a P0P packet with a given command, sequence number, session id, and data.

    Parameters
    ----------
    command : int
        The command number.
    seq : int
        The sequence number.
    session_id : int
        The session id.
    data : str | None
        The data to send with this packet. Default value is None.

    Returns
    -------
    bytes
        The packet.
    """
    return _pack(constants.PACKET_FORMAT, constants.MAGIC_NUMBER, constants.VERSION, command, seq, session_id, data)


def unpack(data: bytes) -> "tuple[int, int, int, int, int]":
    """
    Decodes a P0P packet.

    Returns
    -------
    tuple[int, int, int, int, int]
        A tuple containing the magic number, version number, command, sequence number, and session id.
    """
    return struct.unpack(constants.PACKET_FORMAT, data)


def get_hostname(address: str) -> str:
    """
    Tries to translate the given IPv4 address to a hostname.

    Parameters
    ----------
    address : str
        An IPv4 address.
    Returns
    -------
    str
        The corresponding IPv4 address or the same argument that was passed in to this function.
    """
    ret_address = address
    try:
        ret_address, _, _ = gethostbyaddr(address)
    except:  # pylint: disable=bare-except
        pass
    return ret_address
