#!/usr/bin/env python3
"""
1. Add all PNGs under 'pepes/' (ignoring any existing sub-folders) and grab
   the *images-only* folder CID.
2. Rewrite every metadata/<id> so `image` =
      "ipfs://<images_folder_cid>/<id>.png"
3. Copy the rewritten files to pepes/metadata/<id>
4. Add & pin that 'pepes/metadata/' folder, report its CID.

Run inside the venv:
    python publish_to_ipfs_split.py
"""

import json, shutil, subprocess, pathlib, re, sys, textwrap
from tqdm import tqdm

PEPES_DIR      = pathlib.Path("pepes")
META_SRC_DIR   = pathlib.Path("metadata")          # originals
META_DST_DIR   = PEPES_DIR / "metadata"            # final location
SCHEME         = "ipfs://"
TOTAL_IDS      = 22_065

# ---------------------------------------------------------------------------

def add_images_folder_get_cid() -> str:
    """
    Add 'pepes/' but ignore any sub-folders (there shouldn’t be any yet).
    Returns the folder CID that contains **only PNGs**.
    """
    cmd = [
        "ipfs", "add", "-r", "--cid-version=1", "--pin=true",
        "--ignore", "metadata/**",
        str(PEPES_DIR)
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)

    last = proc.stdout.strip().splitlines()[-1]
    m = re.match(r"added\s+(\S+)\s+pepes$", last)
    if not m:
        sys.exit("❌ Could not parse folder CID from ipfs output.")
    return m.group(1)

def rewrite_and_copy_metadata(img_root_cid: str):
    META_DST_DIR.mkdir(parents=True, exist_ok=True)

    for idx in tqdm(range(1, TOTAL_IDS + 1), desc="rewriting + copying"):
        src = META_SRC_DIR / str(idx)
        if not src.exists():
            tqdm.write(f"missing {src}, skipping")
            continue

        try:
            data = json.loads(src.read_text())
        except json.JSONDecodeError:
            tqdm.write(f"{src} is not valid JSON, skipping")
            continue

        new_uri = f"{SCHEME}{img_root_cid}/{idx}.png"

        replaced = False
        for k in ("image", "image_url", "imageURI"):
            if k in data:
                data[k] = new_uri
                replaced = True
        if not replaced:
            data["image"] = new_uri

        dst = META_DST_DIR / str(idx)
        dst.write_text(json.dumps(data, indent=2))

def add_metadata_subfolder() -> str | None:
    cmd = ["ipfs", "add", "-r", "--cid-version=1", "--pin=true", str(META_DST_DIR)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    last = proc.stdout.strip().splitlines()[-1]
    m = re.match(r"added\s+(\S+)\s+pepes/metadata$", last)
    return m.group(1) if m else None

# ---------------------------------------------------------------------------

def main():
    # Sanity checks
    for p in (PEPES_DIR, META_SRC_DIR):
        if not p.is_dir():
            sys.exit(textwrap.dedent(f"""
            ❌ Required folder '{p}' not found.  Make sure the downloader
            finished correctly before running this script.
            """).strip())

    print("📦 Adding PNGs (only) under 'pepes/' …")
    images_cid = add_images_folder_get_cid()
    print(f"   → images folder CID = {images_cid}")

    print(f"✏️  Rewriting metadata and copying to '{META_DST_DIR}/' …")
    rewrite_and_copy_metadata(images_cid)

    print("📦 Adding 'pepes/metadata/' …")
    meta_root_cid = add_metadata_subfolder()
    if meta_root_cid:
        print(f"✅ Done!")
        print(f"   • images  : ipfs://{images_cid}/<id>.png")
        print(f"   • metadata: ipfs://{meta_root_cid}/<id>")
    else:
        print("✅ Done, but could not parse CID for the metadata folder.")

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(f"ipfs CLI error:\n{e.stdout}\n{e.stderr}")

