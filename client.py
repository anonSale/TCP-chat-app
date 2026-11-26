import socket, threading, json, sys, os


def parse_target(argv):
    """Accepts:  client.py            -> 127.0.0.1:5000
                 client.py host port
                 client.py host:port"""
    host, port = "127.0.0.1", 5000
    if len(argv) > 1:
        host = argv[1]
        if ":" in host:
            host, p = host.rsplit(":", 1)
            port = int(p)
        elif len(argv) > 2:
            port = int(argv[2])
    return host, port


host, port = parse_target(sys.argv)
username = input("Username: ").strip()

try:
    sock = socket.create_connection((host, port), timeout=10)
except OSError as e:
    print(f"Could not connect to {host}:{port} -> {e}")
    sys.exit(1)
sock.settimeout(None)
print(f"Connected to {host}:{port}")


def send(obj):
    sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))


def receive():
    try:
        for line in sock.makefile("r", encoding="utf-8"):
            try:
                m = json.loads(line)
            except ValueError:
                continue
            t = m.get("type")
            if t == "msg":
                print(f"\n[{m.get('from')}] {m.get('text')}")
            elif t == "dm":
                print(f"\n[DM from {m.get('from')}] {m.get('text')}")
            elif t == "dm_sent":
                print(f"\n[DM to {m.get('to')}] {m.get('text')}")
            elif t == "users":
                print("\nOnline:", ", ".join(m.get("users", [])))
            elif t == "error":
                print(f"\n! {m.get('text')}")
            else:
                print(f"\n* {m.get('text')}")
    except OSError:
        pass
    print("\nDisconnected from server.")
    os._exit(0)          # sys.exit() in a thread would not stop the main thread


threading.Thread(target=receive, daemon=True).start()
send({"type": "join", "username": username})
print("Commands: /dm <user> <text>, /users, /quit")

try:
    while True:
        line = input().strip()
        if not line:
            continue
        if line == "/quit":
            break
        elif line == "/users":
            send({"type": "users"})
        elif line.startswith("/dm"):
            parts = line.split(" ", 2)
            if len(parts) < 3:
                print("Usage: /dm <user> <text>")
            else:
                send({"type": "dm", "to": parts[1], "text": parts[2]})
        else:
            send({"type": "msg", "text": line})
except (KeyboardInterrupt, EOFError):
    pass
except OSError:
    print("Connection lost.")
finally:
    sock.close()