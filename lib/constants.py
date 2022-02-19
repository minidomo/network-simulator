from enum import Enum as _Enum

MAGIC_NUMBER = 0xC356
HEADER_SIZE = 12
VERSION = 1
BUFFER_SIZE = 4096
TIMEOUT_INTERVAL = 5


class Command(_Enum):
    DEFAULT = -1
    HELLO = 0
    DATA = 1
    ALIVE = 2
    GOODBYE = 3


class Response(_Enum):
    NORMAL = 0
    IGNORE = 1
    CLOSE = 2
