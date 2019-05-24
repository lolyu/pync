"""netcat-like utility."""
import argparse
import fcntl
import itertools
import os
import select
import socket
import sys

from six.moves import queue


message_queues = queue.Queue()


def server_listen(port):
    """Listen and accept a connection."""
    global server
    addr = (socket.gethostbyname(socket.gethostname()), port)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(1)
    conn, addr = server.accept()
    conn.setblocking(False)
    return conn


def client_connect(address, port):
    """Connect to remote server."""
    global client
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((address, port))
    client.setblocking(False)
    return client


def set_nonblocking(fd):
    """Set fd non-blocking."""
    flag = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)


def main_loop(args):
    """Main loop."""
    if args.listen:
        conn = server_listen(int(args.listen))
    else:
        conn = client_connect(args.connect[0], int(args.connect[1]))
    inputs = [conn, sys.stdin]
    outputs = []
    while inputs:
        set_nonblocking(sys.stdin.fileno())
        set_nonblocking(sys.stdout.fileno())
        readable, writable, exceptional = select.select(inputs, outputs, [])
        if not outputs:
            outputs = [conn] if sys.stdin in readable else [sys.stdout]
        for r in readable:
            msg = os.read(r.fileno(), 4096)
            if msg:
                message_queues.put(msg)
            else:
                sys.exit(0)
        for w in writable:
            try:
                msg = message_queues.get_nowait()
            except queue.Empty:
                pass
            else:
                os.write(w.fileno(), msg)
        for e in exceptional:
            try:
                inputs.remove(e)
                outputs.remove(e)
            except ValueError:
                pass


if __name__ == "__main__":
    class MyMetavar:
        """Better help message for arg parser."""

        def __init__(self):
            self.metavars = ["address", "port"]
            self.iter = itertools.cycle(self.metavars)

        def __str__(self):
            return next(self.iter)

    parser = argparse.ArgumentParser(description="Python netcat-like utility")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-l", "--listen", help="listen on port.")
    group.add_argument("-c", "--connect", nargs=2, metavar=MyMetavar(),
                       type=str, help="connect to (address, port).")
    args = parser.parse_args()
    main_loop(args)
