#!/usr/bin/env python3
"""Probe helper for case-003 (runs INSIDE the guest container).

usage: probe.py <expression>

Connects to 127.0.0.1:6767 (retrying briefly so the server's startup race is
absorbed here), sends the expression as one line, prints the response line.
"""
import socket
import sys
import time


def main() -> int:
    expr = sys.argv[1]
    sock = None
    last_err = None
    for _ in range(20):  # ~5s of retry: wait for the server to start listening
        try:
            sock = socket.create_connection(("127.0.0.1", 6767), timeout=2)
            break
        except OSError as e:
            last_err = e
            time.sleep(0.25)
    if sock is None:
        print(f"could not connect to 127.0.0.1:6767: {last_err}", file=sys.stderr)
        return 3
    sock.settimeout(5)
    sock.sendall((expr + "\n").encode())
    line = b""
    try:
        while not line.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            line += chunk
    except socket.timeout:
        print("server did not respond", file=sys.stderr)
        return 2
    resp = line.decode(errors="replace").splitlines()[0] if line else ""
    print(resp)
    return 0 if resp else 1


if __name__ == "__main__":
    sys.exit(main())
