import json, os, time, urllib.request, zipfile

OWNER = "exepka-beep"
REPO = "granzgram-android-build"
TOKEN = open(r"C:\Users\rgali\WorkBuddy AI\2026-09-20-16-06-24\shapitogram\android-granz\.gh_token").read().strip()


def call(method, path, payload=None, raw=False):
    url = "https://api.github.com" + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "keydump")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = resp.read()
    return body if raw else (json.loads(body) if body else {})


run_id = 39843176051
for attempt in range(40):
    info = call("GET", f"/repos/{OWNER}/{REPO}/actions/runs/{run_id}")
    print(attempt, info["status"], info["conclusion"])
    if info["status"] == "completed":
        break
    time.sleep(8)

arts = call("GET", f"/repos/{OWNER}/{REPO}/actions/runs/{run_id}/artifacts")
print("artifacts:", [(a["name"], a["size_in_bytes"]) for a in arts.get("artifacts", [])])
for a in arts.get("artifacts", []):
    if a["name"] == "server-rsa":
        blob = call("GET", f"/repos/{OWNER}/{REPO}/actions/artifacts/{a['id']}/zip", raw=True)
        out = r"C:\Users\rgali\WorkBuddy AI\2026-09-20-16-06-24\shapitogram\ios-granz\server-rsa.zip"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(blob)
        with zipfile.ZipFile(out) as zf:
            print("members:", zf.namelist())
            pem = zf.read("server-rsa-public.pem")
        open(out.replace(".zip", ".pem"), "wb").write(pem)
        print("pem len:", len(pem))
        print(pem.decode())
