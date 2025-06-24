#!/usr/bin/env python3
"""
Download every
  • https://data.peplicator.fun/metadata/<id>
  • https://data.peplicator.fun/pepes/<id>.png
for IDs 1-22 065, saving to local metadata/ and pepes/ folders.

Usage:
  pip install aiohttp aiofiles tqdm
  python fetch_pepes.py
"""

import asyncio, aiohttp, aiofiles, os, sys
from pathlib import Path
from tqdm.asyncio import tqdm

START, END = 1, 22_065
BASE_META = "https://data.peplicator.fun/metadata/{}"
BASE_PNG  = "https://data.peplicator.fun/pepes/{}.png"
DIR_META  = Path("metadata")
DIR_PNG   = Path("pepes")
MAX_CONCURRENCY = 50

# ---------------------------------------------------------------------------

DIR_META.mkdir(exist_ok=True)
DIR_PNG.mkdir(exist_ok=True)

sem = asyncio.Semaphore(MAX_CONCURRENCY)

async def fetch(session: aiohttp.ClientSession, url: str, outfile: Path):
    if outfile.exists():        # skip duplicates on re-run
        return
    async with sem, session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
        if r.status != 200:
            tqdm.write(f"[{outfile.name}] HTTP {r.status} – {url}")
            return
        data = await r.read()
    async with aiofiles.open(outfile, "wb") as f:
        await f.write(data)

async def worker(id_: int, session: aiohttp.ClientSession):
    await asyncio.gather(
        fetch(session, BASE_META.format(id_), DIR_META / str(id_)),
        fetch(session, BASE_PNG .format(id_), DIR_PNG  / f"{id_}.png"),
    )

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [worker(i, session) for i in range(START, END + 1)]
        for t in tqdm.as_completed(tasks, total=len(tasks), unit="id"):
            await t

if __name__ == "__main__":
    try:
        asyncio.run(main())
        print("✅ Finished!")
    except KeyboardInterrupt:
        sys.exit("\nInterrupted by user")

