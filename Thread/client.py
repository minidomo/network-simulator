from threading import Timer
import socket
import struct
import random

count = 0
header_map = {
    "HELLO": 0,
    "DATA": 1,
    "GOODBYE": 3,
}
MAGIC_CHARACTER = "|"

sID = random.randint(0, 100)


def pack(command, seq, sessionID):
    return struct.pack("!HBBII", 0xC356, 1, command, seq, sessionID)


# https://stackoverflow.com/questions/3393612/run-certain-code-every-n-seconds
def send():
    global count
    data = ["HELLO", "DATA", "GOODBYE"]
    for header_data in data:
        command = header_map[header_data]
        header = pack(command, count, sID)
        msg = ""
        if header_data == "DATA":
            msg = MAGIC_CHARACTER + "something here"
        data_msg = header + msg.encode("utf-8")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(data_msg, ("127.0.0.1", 1234))
        count += 1
    # Timer(5, send).start()


print("Client Starting")
send()
