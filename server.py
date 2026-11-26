import socket, threading, json, os

HOST = "0.0.0.0"
PORT = int(os.environ.get("CHAT_PORT", 5000))
MAX_LINE = 65536                 # longest accepted message line, in characters
clients = {}                     # username -> socket
lock = threading.Lock()


def send(sock, obj):
    """Send one JSON line. Returns False (never raises) if the socket is dead."""
    try:
        sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def remove_user(name, sock):
    with lock:
        if clients.get(name) is sock:
            del clients[name]


def broadcast(obj, exclude=None):
    with lock:
        targets = [(u, s) for u, s in clients.items() if u != exclude]
    for name, s in targets:
        if not send(s, obj):
            remove_user(name, s)      # drop users whose connection is dead


def handle(conn, addr):
    username = None
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    reader = conn.makefile("r", encoding="utf-8")
    try:
        while True:
            line = reader.readline(MAX_LINE)
            if not line:                       # b"" from recv: client closed (FIN)
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if not isinstance(msg, dict):
                    raise ValueError
            except ValueError:
                send(conn, {"type": "error", "text": "invalid JSON"})
                continue

            t = msg.get("type")

            # --- must join first ---
            if username is None:
                name = str(msg.get("username", "")).strip()
                if t != "join" or not name or len(name) > 20:
                    send(conn, {"type": "error", "text": "join with a username (1-20 characters)"})
                    continue
                with lock:
                    taken = name in clients
                    if not taken:
                        clients[name] = conn
                if taken:
                    send(conn, {"type": "error", "text": "username taken"})
                    continue
                username = name
                print(f"{username} joined from {addr}", flush=True)
                send(conn, {"type": "system", "text": f"welcome {username}"})
                broadcast({"type": "system", "text": f"{username} joined"}, exclude=username)
                continue

            # --- normal messages ---
            if t == "msg":
                text = str(msg.get("text", "")).strip()
                if text:
                    broadcast({"type": "msg", "from": username, "text": text}, exclude=username)

            elif t == "dm":
                to = msg.get("to")
                text = str(msg.get("text", "")).strip()
                if not text:
                    continue
                with lock:
                    target = clients.get(to)
                if target is None:
                    send(conn, {"type": "error", "text": f"user '{to}' not found"})
                elif send(target, {"type": "dm", "from": username, "text": text}):
                    send(conn, {"type": "dm_sent", "to": to, "text": text})   # confirmation
                else:
                    remove_user(to, target)
                    send(conn, {"type": "error", "text": f"user '{to}' not found"})

            elif t == "users":
                with lock:
                    names = list(clients)
                send(conn, {"type": "users", "users": names})
            # unknown types are ignored
    except (OSError, ValueError):
        pass                                   # reset / abrupt disconnect / bad bytes
    finally:
        if username:
            remove_user(username, conn)
            broadcast({"type": "system", "text": f"{username} left"})
            print(f"{username} left", flush=True)
        try:
            conn.close()
        except OSError:
            pass
        print(f"closed {addr}", flush=True)


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"listening on {HOST}:{PORT}", flush=True)
    while True:
        conn, addr = srv.accept()              # new socket per client
        print(f"connected {addr}", flush=True)
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()