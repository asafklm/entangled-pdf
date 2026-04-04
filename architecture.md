# Architecture

This document describes the architecture of the EntangledPdf, focusing on the communication protocols and design rationale.

## Overview

EntangledPdf implements a **hybrid HTTP/WebSocket protocol** for LaTeX PDF synchronization. The server mediates between:

- **Editor**: Sends forward sync requests via HTTP (trigger only)
- **Browsers**: Bidirectional real-time communication via WebSocket (receives sync + sends interactions)

## Communication Protocols

### Editor → Server: HTTP POST `/webhook/update`

The `pdf-server sync` command sends forward sync requests via HTTP:

```bash
pdf-server sync document.pdf 42:5:chapter.tex
```

**Why HTTP for Editor Communication?**

1. **Simplicity**: Editors only need to make a simple POST request. No WebSocket library, no connection management, no reconnection logic.

2. **Fire-and-forget semantics**: Forward sync is a one-shot operation ("go to this position"). HTTP's request-response model matches this perfectly.

3. **Editor plugin compatibility**: Most editors can easily trigger HTTP requests from plugins, scripts, or Makefiles. Requiring WebSocket would complicate editor integration significantly.

4. **No state needed**: The editor doesn't need to maintain a persistent connection or receive broadcast messages. It just triggers the sync and exits.

**Message Format**:
```json
{
  "line": 42,
  "col": 5,
  "tex_file": "/path/to/chapter.tex",
  "pdf_file": "/path/to/document.pdf"
}
```

**Authentication**: `X-API-Key` header (shared secret)

### Server → Browsers: WebSocket Broadcast

After processing the HTTP request, the server **broadcasts** the sync result to all connected browsers via WebSocket:

```python
await manager.broadcast({
    "action": "synctex",
    "page": 5,
    "y": 425.5,
    "x": 100.0,
    "timestamp": 1712345678
})
```

**Why WebSocket for Server-to-Browser?**

1. **Multiple viewers**: The server needs to update all connected PDF viewers simultaneously (one-to-many broadcast). HTTP would require polling or multiple connections.

2. **Real-time updates**: Browsers receive sync updates instantly without polling. This is critical for smooth LaTeX editing workflow.

3. **Bidirectional channel**: The same WebSocket connection is reused for inverse search (browser → server), avoiding connection overhead.

4. **Stateful connections**: Browsers maintain long-lived connections while viewing the PDF. WebSocket handles keepalives and reconnection automatically.

### Browser → Server: WebSocket Message

When the user shift+clicks on the PDF, the browser sends an inverse search request:

```json
{
  "action": "inverse_search",
  "page": 5,
  "x": 250.5,
  "y": 400.0
}
```

**Why WebSocket for Browser-to-Server?**

1. **Connection already exists**: The browser already has a WebSocket open for receiving sync updates. Reusing it avoids the overhead of establishing a new HTTP connection for each click.

2. **Low latency**: User interactions require immediate response. WebSocket provides lower latency than HTTP request-response for frequent, small messages.

3. **Session context**: The WebSocket connection carries authentication state (token), eliminating the need to send credentials with every request.

4. **Bidirectional by design**: Inverse search naturally fits the request-response pattern within the persistent WebSocket connection.

## Message Types

### Server → Client Messages

| Action | Trigger | Purpose |
|--------|---------|---------|
| `synctex` | HTTP webhook received | Scroll all browsers to position |
| `reload` | PDF file updated | Refresh all browser views |
| `pong` | Response to client ping | Acknowledge ping with echoed timestamp |

### Client → Server Messages

| Action | Trigger | Purpose |
|--------|---------|---------|
| `inverse_search` | User shift+click/long-press | Open editor at source position |
| `ping` | Keepalive (every 25s) | Verify connection health with timestamp |
| `log` | Rate-limited client events | Debug info (scroll, load, etc.) |

## Protocol Flow Diagrams

### Forward Search (Editor → PDF)

```
┌─────────┐     HTTP POST      ┌─────────┐    WebSocket    ┌─────────┐
│ Editor  │ ─────────────────> │ Server  │ ──────────────> │ Browser │
│ (nvim)  │   /webhook/update  │         │   broadcast     │ (PDF)   │
└─────────┘   line,col,texfile └─────────┘   synctex msg   └─────────┘
                                      │
                                      │ synctex view
                                      v
                                PDF coordinates
```

### Inverse Search (PDF → Editor)

```
┌─────────┐     WebSocket      ┌─────────┐    Shell exec    ┌─────────┐
│ Browser │ ─────────────────> │ Server  │ ──────────────> │ Editor  │
│ (PDF)   │   inverse_search   │         │   nvr --remote   │ (nvim)  │
└─────────┘   page,x,y         └─────────┘   synctex edit   └─────────┘
```

## Connection Keepalive (Unified Ping/Pong Protocol)

EntangledPdf implements a **client-authoritative ping/pong protocol** for connection keepalive:

### Design Rationale

Traditional WebSocket keepalive uses dual ping/pong systems where both client and server can initiate pings. This creates confusion about responsibility and complicates the protocol. The unified approach centralizes keepalive management in the client.

### How It Works

1. **Client sends ping every 25 seconds** (before server's 30s timeout)
   ```json
   {"action": "ping", "timestamp": 1712345678000}
   ```

2. **Server responds with pong** including the echoed timestamp for RTT calculation
   ```json
   {"action": "pong", "timestamp": 1712345678000}
   ```

3. **Server keeps 30s timeout as failsafe** - if no message received in 30s, server closes the connection

4. **Client calculates RTT** from the echoed timestamp for debugging/monitoring

### Benefits

| Aspect | Unified (Client-Authoritative) | Dual System |
|--------|-------------------------------|-------------|
| **Clarity** | Client initiates, server responds | Both can initiate |
| **Latency detection** | Built-in RTT calculation | None |
| **Server load** | Only responds | May initiate pings on timeout |
| **Mobile/tab handling** | Client detects sleep/wake | May miss server pings |

### Message Format

**Client → Server (ping):**
```json
{
  "action": "ping",
  "timestamp": 1712345678000
}
```

**Server → Client (pong):**
```json
{
  "action": "pong",
  "timestamp": 1712345678000
}
```

The timestamp is echoed back unchanged, allowing the client to calculate round-trip time (RTT) for connection health monitoring.

## Rationale for Protocol Split

### Why Not Unify Everything on WebSocket?

While a pure WebSocket architecture is possible, the current hybrid approach is pragmatic:

| Aspect | Current (Hybrid) | Pure WebSocket |
|--------|----------------|----------------|
| **Editor complexity** | Low: simple HTTP POST | High: WS client, reconnect, state mgmt |
| **Connection overhead** | None for editor | New WS connection per sync |
| **Error handling** | HTTP status codes | Custom error protocol |
| **Tooling** | curl, wget, any HTTP lib | Requires WS client library |
| **Make/CI integration** | Easy: `curl -X POST` | Hard: need WS client |

### Why Not Use HTTP for Everything?

Using HTTP polling for browser updates would be inefficient:

| Aspect | Current (WebSocket) | HTTP Polling |
|--------|---------------------|--------------|
| **Latency** | Instant push | Polling delay (100ms+) |
| **Server load** | One connection | Many HTTP requests |
| **Multiple clients** | Single broadcast | N separate responses |
| **Inverse search** | Already connected | New HTTP request per click |

## Security Considerations

- **HTTP endpoints** use `X-API-Key` header for editor authentication
- **WebSocket connections** use token-based auth (query param) when inverse search is enabled
- **Inverse search** only works over WSS (disabled in HTTP mode for security)
- **Tokens** are regenerated on each PDF load and stored in secure, httpOnly cookies

## Key Files

| File | Responsibility |
|------|--------------|
| `src/routes/webhook.py` | HTTP endpoint, SyncTeX forward search |
| `src/routes/websocket.py` | WebSocket handler, inverse search execution |
| `src/connection_manager.py` | Connection pooling, broadcasting |
| `entangledpdf/sync.py` | Editor-side HTTP client library |
| `static/websocket-manager.ts` | Browser-side WebSocket client |
