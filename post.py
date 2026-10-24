"""Post today's generated image to Instagram via the Graph API."""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).parent
HIST_PATH = ROOT / "history.json"

HOST = os.environ.get("GRAPH_HOST", "https://graph.instagram.com")
VERSION = os.environ.get("GRAPH_VERSION", "v23.0")
USER_ID = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_ACCESS_TOKEN"]
BASE_URL = os.environ["PUBLIC_BASE_URL"].rstrip("/")  # folder where output/*.jpg is publicly reachable


def api(method, path, **kwargs):
    r = requests.request(method, f"{HOST}/{VERSION}/{path}", timeout=60, **kwargs)
    if not r.ok:
        raise SystemExit(f"API error {r.status_code}: {r.text}")
    return r.json()


def wait_for_image(url, tries=20):
    for _ in range(tries):
        try:
            r = requests.get(url, timeout=30, stream=True)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                return
        except requests.RequestException:
            pass
        time.sleep(15)
    raise SystemExit(f"Image never became reachable at {url}")


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history = json.loads(HIST_PATH.read_text())
    entry = next((h for h in history if h["date"] == date), None)
    if not entry:
        raise SystemExit(f"No generated image for {date}; run generate.py first")
    if entry.get("posted"):
        print("Already posted, nothing to do")
        return

    image_url = f"{BASE_URL}/{entry['file']}"
    wait_for_image(image_url)

    container = api("POST", f"{USER_ID}/media",
                    data={"image_url": image_url, "caption": entry["caption"], "access_token": TOKEN})
    cid = container["id"]

    for _ in range(30):
        status = api("GET", cid, params={"fields": "status_code", "access_token": TOKEN})["status_code"]
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise SystemExit(f"Container failed: {status}")
        time.sleep(5)

    published = api("POST", f"{USER_ID}/media_publish", data={"creation_id": cid, "access_token": TOKEN})
    entry["posted"] = True
    entry["media_id"] = published["id"]
    HIST_PATH.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    print(f"Posted {entry['file']} -> media id {published['id']}")


if __name__ == "__main__":
    main()
