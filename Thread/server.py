import sys
import socket
import struct

from threading import Thread


def pack(command, seq, sessionID):
    return struct.pack("!HBBII", 0xC356, 1, command, seq, sessionID)


def unpack(data):
    return struct.unpack("!HBBII", data)


count = 0


def sendPacket(command, sessionID, destination, data):
    global count
    header = pack(command, count, sessionID)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(header, destination)
    count += 1


class Client:

    def __init__(self, sessionID, address):
        self.sessionID = sessionID
        self.connected = True
        self.packetNumber = 0
        self.address = address

    def disconnect(self):
        self.connected = False


client_map = {}
MAGIC_NUMBER = 0xC356
MAGIC_CHARACTER = b"|"
max_length = 100


def server_close():
    print("entering server close")
    for client in client_map:
        sendPacket(0, client.sessionID, client.address, None)
    header = pack(5, 0, 0)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(header, ("127.0.0.1", 1234))


def handle_keyboard():
    print("Listening for keyboard input")
    while True:
        text = sys.stdin.readline()
        # Terminates server if input is EOF or 'q'
        if not text or (text == "q\n" and sys.stdin.isatty()):
            server_close()  # do gracefully end here
            break


def handle_socket(local_addr):
    print("New Thread Created")
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_socket.bind(local_addr)
    print("Socket bound")
    while True:
        packet, remote_addr = my_socket.recvfrom(max_length)

        raw_packet = packet.split(MAGIC_CHARACTER, 1)
        magic_num, num, command, seq, sessionId = unpack(raw_packet[0])

        if command == 5:
            break
        if magic_num == MAGIC_NUMBER:
            sessionId_str = str(sessionId)
            if sessionId_str not in client_map and command == 0:
                client_map[sessionId_str] = Client(sessionId, remote_addr)
                print("Received hello")
                sendPacket(0, sessionId, remote_addr, None)
            else:
                client = client_map[sessionId_str]
                if command == 1:
                    if seq < client.packetNumber:
                        server_close()
                        break
                    elif client.packetNumber == seq:
                        print(
                            str(client.sessionID) + " [" + str(seq) +
                            "] Duplicated Packet!")
                    for i in range(client.packetNumber + 1, seq):
                        print(
                            str(client.sessionID) + " [" + str(i) +
                            "] Lost Packet!")
                    print(
                        str(client.sessionID) + " [" + str(seq) + "] " +
                        raw_packet[1].decode("utf-8"))
                    client.packetNumber = seq
                    sendPacket(2, client.sessionID, client.address, None)
                elif command == 3:
                    sendPacket(3, sessionId, remote_addr, None)
                    del client_map[sessionId_str]
                else:
                    server_close()
                    break


if __name__ == "__main__":
    # local_port = int(sys.argv[1])
    print("Server started")
    local_port = 1234
    local_addr = (b"0.0.0.0", local_port)
    t1 = Thread(target=handle_socket, args=(local_addr, ), daemon=True)
    t1.start()

    # start a second thread to handle the keyboard
    t2 = Thread(target=handle_keyboard, daemon=True)
    t2.start()

    while t1.is_alive():
        temp = 1

    print("Server closing")
    # t2 closes when main thread closes
