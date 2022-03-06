"""Benchmarking for RTT."""

import setup_path  # pylint: disable=unused-import
import time
import random
import os
import sys
import subprocess
from lib.structures import ThreadClient


def make_thread_client(portnum) -> ThreadClient:
    client = ThreadClient("localhost", portnum, 1)
    return client


def main():
    portnum = random.randint(60000, 64000)

    r, w = os.pipe()
    ready, w2 = os.pipe()

    pid = os.fork()
    if pid > 0:
        with open("Thread/Dostoyevsky.txt", encoding="utf-8") as file:
            print("not ready")
            ready = os.fdopen(ready)
            w2 = os.fdopen(w2, "w")
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

            with open("temp/rtt_client.txt", "w", encoding="utf-8") as output:
                sys.stdout = output

                for line in file:
                    t = time.time()
                    client.send_data(line)
                    client.receive_packet()
                    times += time.time() - t
                    count += 1
                    resp_time = times / count
                    output.write(f"Average response time: {resp_time}\n")

                # send q to server
                w = os.fdopen(w, "w")
                w.write("q\n")
                w.flush()

    elif pid == 0:
        # handle q from client
        r = os.fdopen(r)
        w2 = os.fdopen(w2, "w")

        with open("temp/rtt_server.txt", "w", encoding="utf-8") as output:
            # subprocess.run(
            #     ["../downlaods/p0-zain-and-jb/Thread/server", str(portnum)], stdin=r, stdout=output,
            #     check=False)  # barebones server
            subprocess.run(["./Thread/server", str(portnum)], stdin=r, stdout=output, check=False)  # finished server
    else:
        print("Fork failed")


if __name__ == "__main__":
    main()
