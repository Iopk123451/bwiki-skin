"""Reliable FTP uploader for InfinityFree.

STOR of anything larger than ~16 bytes is unreliable (451 / silent 0-byte).
This script instead: STORs a 16-byte seed (the first 16 bytes of the file),
APPEnds 1KB chunks, then downloads the remote file and verifies byte equality.
"""
import os
import subprocess
import sys
import time

CHUNK = 1024


def _load_secrets():
    """Read FTP_URL / MW_USER / MW_PASS from a git-ignored .secrets.env."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, ".secrets.env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_secrets()
FTP_URL = os.environ.get("FTP_URL", "")
if not FTP_URL:
    sys.exit("FTP_URL 未配置：请在 mw-build/.secrets.env 写入 "
             "FTP_URL=ftp://user:pass@host/htdocs/")


def ftp_list(path="/"):
    if path and not path.endswith("/"):
        path += "/"
    r = subprocess.run(
        ["curl", "-s", "--connect-timeout", "15", "--max-time", "60", FTP_URL + path],
        capture_output=True,
    )
    return r.stdout.decode("utf-8", "replace")


def remote_size(name, listing=None, dirname=None):
    import posixpath
    import re

    if dirname is None:
        dirname = posixpath.dirname(name)
        name = posixpath.basename(name)
    listing = listing or ftp_list(dirname)
    for line in listing.splitlines():
        parts = line.split()
        if len(parts) >= 9 and parts[-1] == name:
            return int(parts[4])
    return None


def ftp_delete(name):
    subprocess.run(
        ["curl", "-s", "-Q", f"-DELE {name}", "-T", "-", "--connect-timeout", "15",
         "--max-time", "60", FTP_URL + name],
        input=b"",
        capture_output=True,
    )


def curl_upload_append(local_path, remote, append=False):
    cmd = ["curl", "-s", "--connect-timeout", "15", "--max-time", "90"]
    if append:
        cmd.append("-a")
    cmd += ["-T", local_path, FTP_URL + remote]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode


def download(remote, local):
    r = subprocess.run(
        ["curl", "-s", "--connect-timeout", "15", "--max-time", "90",
         FTP_URL + remote, "-o", local],
        capture_output=True,
    )
    return r.returncode


def push(local_path, remote):
    data = open(local_path, "rb").read()
    seed = local_path + ".seed"
    with open(seed, "wb") as fh:
        fh.write(data[:16])

    for attempt in range(6):
        # create the seed file (STOR, tiny => reliable)
        rc = curl_upload_append(seed, remote, append=False)
        size = remote_size(remote)
        if rc == 0 and size == 16:
            break
        print(f"  seed attempt {attempt}: rc={rc} size={size}")
        ftp_delete(remote)
        time.sleep(1)
    else:
        print(f"FAILED to seed {remote}")
        return False

    ok = True
    for i in range(16, len(data), CHUNK):
        part = local_path + ".part"
        with open(part, "wb") as fh:
            fh.write(data[i : i + CHUNK])
        rc = curl_upload_append(part, remote, append=True)
        if rc != 0:
            print(f"  chunk @{i} rc={rc}")
            ok = False
            break
    import os

    os.remove(part)
    os.remove(seed)

    if not ok:
        print(f"FAILED appending {remote}")
        return False

    # verify
    tmp = local_path + ".dl"
    download(remote, tmp)
    remote_data = open(tmp, "rb").read()
    os.remove(tmp)
    if remote_data == data:
        print(f"OK {remote} ({len(data)} bytes, byte-identical)")
        return True
    print(f"MISMATCH {remote}: remote={len(remote_data)} local={len(data)}")
    return False


if __name__ == "__main__":
    failures = 0
    for arg in sys.argv[1:]:
        local, _, remote = arg.partition("=")
        remote = remote or local.replace("\\", "/").split("/")[-1]
        if not push(local, remote):
            failures += 1
    sys.exit(1 if failures else 0)
