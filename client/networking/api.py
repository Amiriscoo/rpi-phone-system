import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "client.json"
TOKEN_PATH = ROOT / "config" / "session.json"
QUEUE_PATH = ROOT / "config" / "message_queue.json"

class Api:
    def __init__(self):
        self.config = json.loads(CONFIG_PATH.read_text())
        self.base_url = self.config["server_url"].rstrip("/")
        self.token = ""
        self.user_id = None
        if TOKEN_PATH.exists():
            saved = json.loads(TOKEN_PATH.read_text())
            self.token, self.user_id = saved.get("token", ""), saved.get("user_id")

    @property
    def online(self):
        return bool(self.token)

    def _request(self, method, path, body=None):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.base_url + path, method=method, headers=headers)
        if body is not None:
            request.data = json.dumps(body).encode()
        with urlopen(request, timeout=4) as response:
            return json.loads(response.read().decode())

    def login(self, username, password, register=False):
        result = self._request("POST", "/auth/register" if register else "/auth/login", {"username": username, "password": password})
        self.token, self.user_id = result["token"], result["user_id"]
        TOKEN_PATH.write_text(json.dumps({"token": self.token, "user_id": self.user_id}))
        return result

    def get(self, path):
        return self._request("GET", path)

    def post(self, path, body):
        return self._request("POST", path, body)

    def queue_message(self, recipient_id, body):
        queued = []
        if QUEUE_PATH.exists():
            queued = json.loads(QUEUE_PATH.read_text())
        queued.append({"recipient_id": recipient_id, "body": body})
        QUEUE_PATH.write_text(json.dumps(queued))

    def flush_message_queue(self):
        if not QUEUE_PATH.exists() or not self.token:
            return 0
        queued = json.loads(QUEUE_PATH.read_text())
        remaining = []
        sent = 0
        for message in queued:
            try:
                self.post(f"/messages/{message['recipient_id']}", {"body": message["body"]})
                sent += 1
            except (HTTPError, URLError):
                remaining.append(message)
        if remaining:
            QUEUE_PATH.write_text(json.dumps(remaining))
        else:
            QUEUE_PATH.unlink()
        return sent

    def logout(self):
        self.token, self.user_id = "", None
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()

    def error_text(self, error):
        if isinstance(error, HTTPError):
            try:
                return json.loads(error.read().decode()).get("detail", "Server error")
            except Exception:
                return f"Server error ({error.code})"
        if isinstance(error, URLError):
            return "Server unreachable. Check Wi-Fi or Tailscale."
        return str(error)
