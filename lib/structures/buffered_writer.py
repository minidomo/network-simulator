"""A thread-safe and buffered printer."""

from queue import Queue


class BufferedWriter:
    """
    A thread-safe and buffered printer.
    """

    def __init__(self, fd: "int|None", buffer_size: int, encoding: str) -> None:
        """
        Creates a thread-safe and buffered printer with a given file descriptor, mode, buffer size, and encoding
        scheme.

        Parameters
        ----------
        fd : int | None
            The file descriptor.
        buffer_size : int
            The size of the buffer.
        encoding : str
            The encoding scheme.
        """
        self._queue = Queue()
        if fd is not None:
            self._stream = open(fd, "w", buffering=buffer_size, encoding=encoding)  # pylint: disable=consider-using-with

    def write(self, s: str) -> None:
        """
        Appends the given string to the queue.
        """
        self._queue.put(s)

    def flush(self, limit: "int|None" = None) -> None:
        """
        Flushes the queue and writes strings to the file descriptor.

        Parameters
        ----------
        limit : int | None
            The number of strings to print from the queue. Default is None. If None, prints all current strings in
            the queue. If limit is defined to an int, this will print at most the given limit.
        """
        size = self._queue.qsize() if limit is None else min(limit, self._queue.qsize())
        if size > 0:
            for _ in range(size):
                s: str = self._queue.get()
                self._stream.write(s)
                self._stream.write("\n")
            self._stream.flush()

    def close(self) -> None:
        """
        Flushes any remaining strings in the queue and closes the file descriptor.
        """
        self.flush()
        self._stream.close()
