#!/usr/bin/env python3
"""Simple TCP proxy for Chrome CDP: listens on 0.0.0.0:9223, forwards to 127.0.0.1:9222.
Run this on Windows so WSL can reach Chrome CDP via the Windows host IP."""
import socket
import threading
import sys

LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 9223
TARGET_HOST = '127.0.0.1'
TARGET_PORT = 9222

def forward(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass

def handle_client(client_sock):
    try:
        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target.connect((TARGET_HOST, TARGET_PORT))
        t1 = threading.Thread(target=forward, args=(client_sock, target), daemon=True)
        t2 = threading.Thread(target=forward, args=(target, client_sock), daemon=True)
        t1.start()
        t2.start()
        t1.join()
    except Exception as e:
        print(f"Connection error: {e}", file=sys.stderr)
        try: client_sock.close()
        except: pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(5)
    print(f"CDP Proxy: {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}", flush=True)
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

if __name__ == '__main__':
    main()
