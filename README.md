# Network Simulator

Initialize a server and allow clients to connect and send messages to the server using UDP and following a protocol created by the professor. The server is implemented using threads, and the client is implemented in two ways, threads and events. 

## Running

Start the server:

```
./Thread/server <port>
```

Start a thread-based client:

```
./Thread/client <address> <port>
```

Start the event-based client:

```
./Event/client <address> <port>
```

## Testing

Run tests from the root directory:

```
pytest
```