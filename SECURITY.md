# Security

pyxel-mcp is an observation adapter for local development. Tools that accept
a `script` argument execute that Python file in a subprocess with your user
privileges. Subprocess isolation keeps Pyxel state from leaking between tool
calls; it is **not** a sandbox for untrusted code. Only point the tools at
scripts you trust.

To report a vulnerability, please use GitHub private vulnerability reporting
(https://github.com/kitao/pyxel-mcp/security/advisories/new) instead of a
public issue.
