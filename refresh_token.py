"""Refresh the long-lived Instagram token. Prints ONLY the new token to stdout."""
import os
import sys

import requests

HOST = os.environ.get("GRAPH_HOST", "https://graph.instagram.com")

r = requests.get(
    f"{HOST}/refresh_access_token",
    params={"grant_type": "ig_refresh_token", "access_token": os.environ["IG_ACCESS_TOKEN"]},
    timeout=60,
)
if not r.ok:
    sys.exit(f"Refresh failed ({r.status_code}): {r.text}")

data = r.json()
print(f"New token valid for {data.get('expires_in', '?')} seconds", file=sys.stderr)
print(data["access_token"])
