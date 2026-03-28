"""Minimal OAuth callback HTTP server.

Run as an ephemeral Docker container by clawforce during an OAuth login flow::

    docker run --rm -p 1455:1455 \\
        -e OAUTH_NOTIFY_URL=http://host.docker.internal:8080/api/providers/oauth/internal/deliver \\
        -e OAUTH_PORT=1455 \\
        clawforce:latest python -m clawforce.oauth_callback_server

Environment variables
---------------------
OAUTH_NOTIFY_URL
    The clawforce endpoint to POST ``{"code": "...", "state": "..."}`` to once
    the browser lands on ``/auth/callback``.
OAUTH_PORT
    Port to listen on (default: 1455).
"""

import http.client
import http.server
import json
import os
import urllib.parse

NOTIFY_URL: str = os.environ.get("OAUTH_NOTIFY_URL", "")
PORT: int = int(os.environ.get("OAUTH_PORT", "1455"))

_SUCCESS_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Authorization successful</title>
  <style>
    body{font-family:system-ui,sans-serif;display:flex;align-items:center;
         justify-content:center;min-height:100vh;margin:0;background:#f8fafc;}
    .card{text-align:center;padding:2.5rem 3rem;background:white;
          border-radius:1rem;box-shadow:0 4px 24px rgba(0,0,0,.08);max-width:420px;}
    .icon{font-size:3rem;margin-bottom:1rem;}
    h1{font-size:1.4rem;margin:0 0 .5rem;}
    p{color:#64748b;margin:0 0 1.5rem;font-size:.95rem;}
    button{background:#6366f1;color:white;border:none;border-radius:.5rem;
           padding:.6rem 1.6rem;font-size:.9rem;cursor:pointer;}
    button:hover{background:#4f46e5;}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">&#10003;</div>
    <h1>Authorization successful</h1>
    <p>You can close this tab and return to clawforce.</p>
    <button onclick="window.close()">Close tab</button>
  </div>
</body>
</html>"""

_ERROR_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Authorization error</title>
  <style>
    body{font-family:system-ui,sans-serif;display:flex;align-items:center;
         justify-content:center;min-height:100vh;margin:0;background:#fef2f2;}
    .card{text-align:center;padding:2.5rem 3rem;background:white;
          border-radius:1rem;box-shadow:0 4px 24px rgba(0,0,0,.08);max-width:420px;}
    h1{font-size:1.4rem;color:#dc2626;margin:0 0 .5rem;}
    p{color:#64748b;margin:0;font-size:.9rem;}
  </style>
</head>
<body>
  <div class="card">
    <h1>Authorization failed</h1>
    <p>The provider returned an error. Please close this tab and try again.</p>
  </div>
</body>
</html>"""


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/auth/callback"):
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)
        code = (params.get("code") or [""])[0]
        state = (params.get("state") or [""])[0]
        error = (params.get("error") or [""])[0]

        if error or not code:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_ERROR_HTML)
            return

        if code and state and NOTIFY_URL:
            try:
                parsed_notify = urllib.parse.urlparse(NOTIFY_URL)
                host = parsed_notify.netloc
                path = parsed_notify.path or "/"
                payload = json.dumps({"code": code, "state": state}).encode()
                conn = http.client.HTTPConnection(host, timeout=10)
                conn.request(
                    "POST",
                    path,
                    body=payload,
                    headers={"Content-Type": "application/json"},
                )
                conn.getresponse()
            except Exception:
                pass

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_SUCCESS_HTML)

    def log_message(self, *_args: object) -> None:
        pass


def main() -> None:
    server = http.server.HTTPServer(("0.0.0.0", PORT), _CallbackHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
