import socket, threading, json, os

HOST, PORT = "0.0.0.0", int(os.environ.get("CHAT_PORT", 5000))
clients = {}                 # username -> socket
lock = threading.Lock()

def send(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))

def broadcast(obj, exclude=None):
    with lock:
        targets = [s for u, s in clients.items() if u != exclude]
    for s in targets:
        try: send(s, obj)
        except OSError: pass

def handle(conn, addr):
    username = None
    reader = conn.makefile("r", encoding="utf-8")   # splits stream on "\n"
    try:
        for line in reader:                          # ends when client closes (recv returns b"")
            try: msg = json.loads(line)
            except json.JSONDecodeError:
                send(conn, {"type": "error", "text": "invalid JSON"}); continue

            t = msg.get("type")
            if username is None:                     # must join first
                name = str(msg.get("username", "")).strip()
                with lock:
                    ok = t == "join" and name and name not in clients
                    if ok: clients[name] = conn
                if not ok:
                    send(conn, {"type": "error", "text": "join with a unique username"}); continue
                username = name
                send(conn, {"type": "system", "text": f"welcome {username}"})
                broadcast({"type": "system", "text": f"{username} joined"}, exclude=username)
            elif t == "msg":
                broadcast({"type": "msg", "from": username, "text": msg.get("text", "")}, exclude=username)
            elif t == "dm":
                with lock: target = clients.get(msg.get("to"))
                if target: send(target, {"type": "dm", "from": username, "text": msg.get("text", "")})
                else: send(conn, {"type": "error", "text": "user not found"})
            elif t == "users":
                with lock: names = list(clients)
                send(conn, {"type": "users", "users": names})
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass                                         # abrupt disconnect
    finally:
        if username:
            with lock: clients.pop(username, None)
            broadcast({"type": "system", "text": f"{username} left"})
        conn.close()
        print(f"closed {addr}")

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"listening on {HOST}:{PORT}")
    while True:
        conn, addr = srv.accept()                    # one new socket per client
        print(f"connected {addr}")
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()