from queue import Queue as _Queue


class BufferedWriter:

    def __init__(self, fd: int, mode: str, buffer_size: int, encoding: str) -> None:
        self.__queue = _Queue()
        self.__stream = open(fd, mode, buffering=buffer_size, encoding=encoding)  # pylint: disable=consider-using-with

    def write(self, s: str) -> None:
        self.__queue.put(s)

    def flush(self, limit: int = None) -> None:
        size = self.__queue.qsize() if limit is None else min(limit, self.__queue.qsize())
        if size > 0:
            for _ in range(size):
                s: str = self.__queue.get()
                self.__stream.write(s)
                self.__stream.write("\n")
            self.__stream.flush()

    def close(self) -> None:
        self.flush()
        self.__stream.close()
