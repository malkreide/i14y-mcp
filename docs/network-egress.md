# Network egress

`i14y-mcp` reaches exactly **one** external host. Egress is controlled on two
layers (SEC-021).

## Allow-listed hosts

| Host | Purpose |
|---|---|
| `api.i14y.admin.ch` | The I14Y interoperability platform read API (HTTPS) |

## Code layer

The allow-list is a `frozenset` in [`src/i14y_mcp/client.py`](../src/i14y_mcp/client.py)
— **not** configurable via environment variables, so an operator mistake or a
tampered config cannot silently widen it:

```python
ALLOWED_HOSTS = frozenset({"api.i14y.admin.ch"})
```

- `assert_host_allowed()` runs before the HTTP client is built.
- The client is created with `follow_redirects=False`; a `3xx` response is
  surfaced as an error instead of being followed off the allow-listed host.
- Every request targets the fixed `BASE_URL` with a relative path only — no tool
  accepts a user-supplied URL, so there is no SSRF surface.

## Network layer

For hosted (SSE / streamable-http) deployments, add an egress control at the
platform layer as defense in depth:

- **Kubernetes:** a `NetworkPolicy` allowing egress only to `api.i14y.admin.ch`
  (plus DNS to the cluster resolver on UDP/TCP 53 — otherwise hostname
  resolution breaks).
- **Cloud (Render/Railway/etc.):** a security-group / firewall egress rule to the
  same host, or route outbound traffic through a filtering proxy.

## Changing the allow-list

Adding a host is a reviewed code change:

1. Add the hostname to `ALLOWED_HOSTS` in `client.py`.
2. Add a row to the table above.
3. Update the network-layer policy to match.
4. Note the change in `CHANGELOG.md`.
