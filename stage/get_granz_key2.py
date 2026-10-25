import json, os, urllib.request, zipfile

OWNER = "exepka-beep"
REPO = "granzgram-android-build"
TOKEN = open(r"C:\Users\rgali\WorkBuddy AI\2026-09-20-16-06-24\shapitogram\android-granz\.gh_token").read().strip()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "keydump")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read())


run_id = 39843176051
info = api(f"/repos/{OWNER}/{REPO}/actions/runs/{run_id}")
print("run:", info["status"], info["conclusion"])

arts = api(f"/repos/{OWNER}/{REPO}/actions/runs/{run_id}/artifacts")
print("artifacts:", [(a["name"], a["size_in_bytes"]) for a in arts.get("artifacts", [])])
art = [a for a in arts["artifacts"] if a["name"] == "server-rsa"][0]

opener = urllib.request.build_opener(NoRedirect)
req = urllib.request.Request(
    f"https://api.github.com/repos/{OWNER}/{REPO}/actions/artifacts/{art['id']}/zip")
req.add_header("Authorization", "token " + TOKEN)
req.add_header("User-Agent", "keydump")
try:
    opener.open(req, timeout=60)
    raise SystemExit("expected a redirect")
except urllib.error.HTTPError as err:
    if err.code not in (301, 302, 303, 307, 308):
        raise
    location = err.headers["Location"]
print("redirect ok, downloading blob...")

with urllib.request.urlopen(location, timeout=120) as resp:
    blob = resp.read()
print("blob bytes:", len(blob))

out = r"C:\Users\rgali\WorkBuddy AI\2026-09-20-16-06-24\shapitogram\ios-granz\server-rsa.zip"
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "wb").write(blob)
with zipfile.ZipFile(out) as zf:
    print("members:", zf.namelist())
    pem = zf.read("server-rsa-public.pem")
open(out.replace(".zip", ".pem"), "wb").write(pem)
print("pem len:", len(pem))
print(pem.decode())
