# Chat Protocol Specification

## 1. Transport and framing

- Transport: TCP (SOCK_STREAM), server listens on port 5000 (internally).
- Public access on Railway is through a TCP Proxy that forwards a public
  port to port 5000.
- Encoding: UTF-8.
- Message format: one JSON object per line, terminated by `\n`.
- Why newline framing: TCP is a byte stream with no message boundaries,
  so one `recv()` may return half a message or several. The `\n`
  delimiter lets the receiver split the stream into messages.
  `json.dumps` escapes newlines inside strings, so `\n` never appears
  within a message body.
- Every message has a `"type"` field.

## 2. Connection lifecycle

1. Client opens a TCP connection.
2. Client must send a `join` message first. All other messages are
   rejected until a join succeeds.
3. Server replies with a `system` welcome and notifies other users.
4. Client sends `msg`, `dm`, and `users` messages freely.
5. Client closes the connection (`/quit`, Ctrl+C, or crash).
6. Server detects the close, removes the user, and broadcasts a
   "left" notice.

## 3. Client → Server messages

| Type | Fields | Description |
|---|---|---|
| `join` | `username` (string) | Register a nickname. Must be non-empty and not already in use. |
| `msg` | `text` (string) | Send a message to all other users (group chat). |
| `dm` | `to` (string), `text` (string) | Send a private message to one user. |
| `users` | none | Request the list of online users. |

Examples:

```json
{"type":"join","username":"alice"}
{"type":"msg","text":"hello all"}
{"type":"dm","to":"bob","text":"hi"}
{"type":"users"}
```

## 4. Server → Client messages

| Type | Fields | Sent when |
|---|---|---|
| `msg` | `from`, `text` | Another user sends a group message. Not echoed to the sender. |
| `dm` | `from`, `text` | Another user sends you a private message. |
| `users` | `users` (array of strings) | Reply to a `users` request. |
| `system` | `text` | Welcome, user joined, user left. |
| `error` | `text` | A request was invalid (see section 5). |

Examples:

```json
{"type":"msg","from":"alice","text":"hello all"}
{"type":"dm","from":"alice","text":"hi"}
{"type":"users","users":["alice","bob"]}
{"type":"system","text":"bob joined"}
{"type":"error","text":"user not found"}
```

## 5. Error handling

| Error text | Cause |
|---|---|
| `invalid JSON` | A line could not be parsed as JSON. Connection stays open. |
| `join with a unique username` | Join missing, empty, or name already taken. |
| `user not found` | `dm` target is not online. |

Unrecognized message types are ignored.

## 6. Disconnection

- Clean close: the client sends a FIN, the server's read returns
  end-of-stream, and the server cleans up.
- Abrupt close (crash, network drop, RST): the server catches the
  socket error and runs the same cleanup.
- In both cases the username is freed and the other users receive
  `{"type":"system","text":"<name> left"}`.

## 7. Example session

```
C(alice) -> {"type":"join","username":"alice"}
S -> alice {"type":"system","text":"welcome alice"}
C(bob)   -> {"type":"join","username":"bob"}
S -> bob   {"type":"system","text":"welcome bob"}
S -> alice {"type":"system","text":"bob joined"}
C(alice) -> {"type":"msg","text":"hello"}
S -> bob   {"type":"msg","from":"alice","text":"hello"}
C(bob)   -> {"type":"dm","to":"alice","text":"hey"}
S -> alice {"type":"dm","from":"bob","text":"hey"}
(bob disconnects)
S -> alice {"type":"system","text":"bob left"}
```

## 8. Known limitations

- No encryption: messages are plain text (TLS would fix this).
- No authentication: anyone can claim any unused username.
- No maximum message length or rate limiting.
- Messages are not persisted; offline users miss them.