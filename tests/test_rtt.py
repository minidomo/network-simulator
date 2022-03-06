import time
import random
import os
import sys
import subprocess
from time import sleep
from threading import Thread
from lib.constants import Command, Response
from lib.structures import Server, BufferedWriter, ClientData, ThreadClient
from lib import constants
from lib import util


def make_thread_client(portnum) -> ThreadClient:
    client = ThreadClient("localhost", portnum, 1)
    return client


def test_one_at_a_time():
    portnum = random.randint(60000, 64000)

    r, w = os.pipe()
    ready, w2 = os.pipe()

    id = os.fork()
    if id > 0:
        file = open("Thread/Dostoyevsky.txt")

        print("not ready")
        ready = os.fdopen(ready)
        w2 = os.fdopen(w2, 'w')
        w2.write("M")
        w2.flush()

        time.sleep(2)

        print("ready ")

        sys.stdout.flush()

        client = make_thread_client(portnum)

        client.send_hello()

        packet, remote_addr = client.receive_packet()
        client.handle_packet(packet, remote_addr)

        count = 0
        times = 0

        output = open("temp/rtt_client.txt", "w")

        sys.stdout = output

        for line in file:
            t = time.time()
            client.send_data(line)
            client.receive_packet()
            times += time.time() - t
            count += 1
            print("Average response time: ", times / count)

        # send q to server
        w = os.fdopen(w, 'w')
        w.write("q\n")
        w.flush()

        print("Average response time: ", times / count)
    elif id == 0:
        # handle q from client
        r = os.fdopen(r)
        sys.stdin = r
        w2 = os.fdopen(w2, 'w')

        output = open("temp/rtt_server.txt", "w")

        # subprocess.run(["../downlaods/p0-zain-and-jb/Thread/server", str(portnum)], stdout=output) # barebones server
        subprocess.run(["./Thread/server", str(portnum)], stdout=output)  # finished server
    else:
        print("Fork failed")
