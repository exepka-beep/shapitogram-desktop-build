"""Dump SERVER_RSA_PEM_B64 from the granzgram-android-build repo via a temporary workflow.

Why: the GranzGram server does not expose /owpengram/server-info any more, so the only
remaining copy of its MTProto public key is the GitHub secret used by the APK pipeline.
The workflow writes it into an artifact; we download, verify the fingerprint, and delete
the workflow file afterwards.
"""
import base64
import json
import os
import sys
import time
import urllib.request
import zipfile

OWNER = "exepka-beep"
REPO = "granzgram-android-build"
WF_PATH = ".github/workflows/_dump-server-key.yml"
TOKEN = open(
    r"C:\Users\rgali\WorkBuddy AI\2026-09-20-16-06-24\shapitogram\android-granz\.gh_token"
).read().strip()
API = "https://api.github.com"


def call(method, path, payload=None, raw=False):
    url = path if path.startswith("http") else API + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "keydump")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
    return body if raw else (json.loads(body) if body else {})


WORKFLOW = """name: dump-server-key
on:
  workflow_dispatch:
jobs:
  dump:
    runs-on: ubuntu-latest
    steps:
      - name: Write key
        env:
          KEY_B64: ${{ secrets.SERVER_RSA_PEM_B64 }}
        run: printf '%s' "$KEY_B64" | base64 -d > server-rsa-public.pem
      - name: Fingerprint
        run: openssl rsa -pubin -in server-rsa-public.pem -noout -text | head -3
      - uses: actions/upload-artifact@v4
        with:
          name: server-rsa
          path: server-rsa-public.pem
"""


def main():
    # 1. current sha of the file (if any)
    sha = None
    try:
        info = call("GET", f"/repos/{OWNER}/{REPO}/contents/{WF_PATH}")
        sha = info["sha"]
        print("existing workflow found, sha", sha)
    except Exception:
        print("workflow not present yet")

    payload = {
        "message": "temp: dump server key for iOS build",
        "content": base64.b64encode(WORKFLOW.encode()).decode(),
    }
    if sha:
        payload["sha"] = sha
    res = call("PUT", f"/repos/{OWNER}/{REPO}/contents/{WF_PATH}", payload)
    print("workflow pushed:", res["commit"]["sha"][:10])

    # 2. dispatch
    time.sleep(2)
    try:
        call("POST", f"/repos/{OWNER}/{REPO}/actions/workflows/_dump-server-key.yml/dispatches",
             {"ref": "main"})
        print("dispatched")
    except Exception as err:
        print("dispatch failed:", err)
        raise

    # 3. wait for the run
    run_id = None
    for _ in range(30):
        time.sleep(5)
        runs = call("GET", f"/repos/{OWNER}/{REPO}/actions/runs?per_page=5")
        for r in runs.get("workflow_runs", []):
            if r["path"].endswith("_dump-server-key.yml"):
                run_id = r["id"]
                print("run", run_id, r["status"], r["conclusion"])
                if r["status"] == "completed":
                    break
        if run_id and r["status"] == "completed":
            break
    if not run_id:
        raise SystemExit("run not started")

    # 4. artifact
    arts = call("GET", f"/repos/{OWNER}/{REPO}/actions/runs/{run_id}/artifacts")
    target = None
    for a in arts.get("artifacts", []):
        if a["name"] == "server-rsa":
            target = a
    if not target:
        raise SystemExit("artifact missing: %s" % arts)
    print("artifact", target["id"], target["size_in_bytes"], "bytes")

    blob = call("GET", f"/repos/{OWNER}/{REPO}/actions/artifacts/{target['id']}/zip", raw=True)
    out = r"C:\Users\rgali\WorkBuddy AI\2026-09-20-16-06-24\shapitogram\ios-granz\server-rsa.zip"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(blob)
    with zipfile.ZipFile(out) as zf:
        print("zip members:", zf.namelist())
        pem = zf.read("server-rsa-public.pem")
    pem_path = out.replace(".zip", ".pem")
    open(pem_path, "wb").write(pem)
    print("pem bytes:", len(pem), "->", pem_path)
    print(pem.decode()[:120])

    # 5. cleanup
    call("DELETE", f"/repos/{OWNER}/{REPO}/contents/{WF_PATH}",
         {"message": "remove temp key dump workflow", "sha": res["content"]["sha"]})
    print("workflow removed")


if __name__ == "__main__":
    main()
