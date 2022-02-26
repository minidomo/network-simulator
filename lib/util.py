import struct as _struct
from . import constants as _Constants


def _pack(format: str, magic: int, version: int, command: int, seq: int, session_id: int, data: str = None) -> bytes:
    header = _struct.pack(format, magic, version, command, seq, session_id)
    if data is None:
        return header
    return header + data.encode("utf-8", "replace")


def pack(command: int, seq: int, session_id: int, data: str = None) -> bytes:
    return _pack(_Constants.PACKET_FORMAT, _Constants.MAGIC_NUMBER, _Constants.VERSION, command, seq, session_id, data)


def unpack(data: bytes) -> "tuple[int, int, int, int, int]":
    return _struct.unpack(_Constants.PACKET_FORMAT, data)
