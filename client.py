import socket, threading, json, sys

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
username = input("Username: ").strip()

sock = socket.create_connection((host, port))
send = lambda o: sock.sendall((json.dumps(o) + "\n").encode())

def receive():
    for line in sock.makefile("r", encoding="utf-8"):
        m = json.loads(line)
        t = m["type"]
        if t == "msg":     print(f"\n[{m['from']}] {m['text']}")
        elif t == "dm":    print(f"\n[DM from {m['from']}] {m['text']}")
        elif t == "users": print("\nOnline:", ", ".join(m["users"]))
        else:              print(f"\n* {m['text']}")
    print("\nDisconnected from server."); sys.exit(0)

threading.Thread(target=receive, daemon=True).start()
send({"type": "join", "username": username})
print("Commands: /dm <user> <text>, /users, /quit")

try:
    while True:
        line = input()
        if line == "/quit": break
        elif line == "/users": send({"type": "users"})
        elif line.startswith("/dm "):
            _, to, text = line.split(" ", 2); send({"type": "dm", "to": to, "text": text})
        else: send({"type": "msg", "text": line})
finally:
    sock.close()