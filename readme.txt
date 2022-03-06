   A: JB Ladera
   B: Zain Bashir

To start the thread-based server: ./Thread/server <portnum>
To start the thread-based client: ./Thread/client <address> <portnum>
To start the event-based client: ./Event/client <address> <portnum>

To run tests, install pytest and run it in the root directory of this project:
$ pytest

.        
├── Event
│   └── client                      - Event-Based Client Runner
├── Thread
│   ├── Dostoyevsky.txt
│   ├── client                      - Thread-Based Client Runner
│   └── server                      - Thread-Based Server Runner
├── lib
│   ├── constants.py
│   ├── structures
│   │   ├── buffered_writer.py      - Handles printing
│   │   ├── client.py               - The base Client class that the thread-based and event-based clients extend
│   │   ├── client_data.py          - The ClientData class that represents a server session
│   │   ├── event_client.py         - The event-based client
│   │   ├── server.py               - The server
│   │   └── thread_client.py        - The thread-based client
│   └── util.py                     - Contains common code such as creating packets
├── p0p-design-test-doc.pdf         - Design Doc
├── readme.txt                      - This file
├── scripts
│   ├── benchmark_rtt.py            - Checks the response time of the server on localhost
│   ├── expect
│   │   ├── Dostoyevsky.exp
│   │   ├── naive.exp
│   │   └── server.exp
│   ├── packet-loss.js              - Calculates packet loss statistics given a file of server output
│   ├── run-clients.js              - Runs multiple clients to test with
│   └── stresstest.bat              - Runs multiple clients and servers at the same time on the same machine
└── tests
    ├── test_event_client.py        - Event-based client tests
    ├── test_server.py              - Thread-based server tests
    └── test_thread_client.py       - Thread-based client tests