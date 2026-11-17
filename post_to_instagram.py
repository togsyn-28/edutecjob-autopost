"""
Publishes one image + caption to Instagram using the official Instagram API.

Needs these environment variables (set them as GitHub secrets, never in this file):
  IG_USER_ID       your Instagram professional account ID
  IG_ACCESS_TOKEN  a long-lived access token for that account
Optional:
  GRAPH_HOST       graph.instagram.com (default, "Instagram Login" tokens)
                   or graph.facebook.com (tokens made through a Facebook Page)
  GRAPH_VERSION    API version, default v23.0

Usage:
  python3 post_to_instagram.py --image-url https://.../day-001.png --caption-file caption.txt
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def call(method, url, params):
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit("Instagram API error %s: %s" % (e.code, body))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-url", required=True)
    ap.add_argument("--caption-file", required=True)
    args = ap.parse_args()

    user_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not user_id or not token:
        sys.exit("IG_USER_ID and IG_ACCESS_TOKEN must be set.")
    host = os.environ.get("GRAPH_HOST") or "graph.instagram.com"
    version = os.environ.get("GRAPH_VERSION") or "v23.0"
    base = "https://%s/%s" % (host, version)

    with open(args.caption_file, encoding="utf-8") as f:
        caption = f.read()

    # 1. Upload: Instagram downloads the image from the public URL.
    container = call("POST", "%s/%s/media" % (base, user_id), {
        "image_url": args.image_url, "caption": caption, "access_token": token})
    cid = container["id"]
    print("Created media container", cid)

    # 2. Wait until Instagram has processed it.
    for _ in range(30):
        status = call("GET", "%s/%s" % (base, cid), {
            "fields": "status_code", "access_token": token}).get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            sys.exit("Instagram could not process the image (status %s)." % status)
        time.sleep(5)
    else:
        sys.exit("Timed out waiting for Instagram to process the image.")

    # 3. Publish.
    result = call("POST", "%s/%s/media_publish" % (base, user_id), {
        "creation_id": cid, "access_token": token})
    print("Published! Instagram media id:", result.get("id"))


if __name__ == "__main__":
    main()
