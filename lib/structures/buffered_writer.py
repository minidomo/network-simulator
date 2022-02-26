from queue import Queue as _Queue


class BufferedWriter:

    def __init__(self, fd: int, mode: str, buffer_size: int, encoding: str) -> None:
        self._queue = _Queue()
        self._stream = open(fd, mode, buffering=buffer_size, encoding=encoding)  # pylint: disable=consider-using-with

    def write(self, s: str) -> None:
        self._queue.put(s)

    def flush(self, limit: int = None) -> None:
        size = self._queue.qsize() if limit is None else min(limit, self._queue.qsize())
        if size > 0:
            for _ in range(size):
                s: str = self._queue.get()
                self._stream.write(s)
                self._stream.write("\n")
            self._stream.flush()

    def close(self) -> None:
        self.flush()
        self._stream.close()
