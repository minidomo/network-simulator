"""Utility methods for encoding and decoding packets."""

import struct as _struct
from . import constants as _Constants


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
    header = _struct.pack(packet_format, magic, version, command, seq, session_id)
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
    return _pack(_Constants.PACKET_FORMAT, _Constants.MAGIC_NUMBER, _Constants.VERSION, command, seq, session_id, data)


def unpack(data: bytes) -> "tuple[int, int, int, int, int]":
    """
    Decodes a P0P packet.

    Returns
    -------
    tuple[int, int, int, int, int]
        A tuple containing the magic number, version number, command, sequence number, and session id.
    """
    return _struct.unpack(_Constants.PACKET_FORMAT, data)
