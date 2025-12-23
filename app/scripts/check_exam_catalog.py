from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from app.services.exam_price_catalog import ExamPriceCatalog, PRICE_SOURCE_URL, CACHE_FILE, CACHE_TTL_SECONDS


def human_ts(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "unknown"


async def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Check exam price catalog availability")
    parser.add_argument("sample", nargs="?", default="血常规", help="Sample exam name to lookup")
    parser.add_argument("--force-refresh", action="store_true", help="Force re-download the catalog")
    args = parser.parse_args()

    catalog = ExamPriceCatalog()
    cache_path = Path(os.getenv("EXAM_PRICE_CACHE_PATH", CACHE_FILE))
    print(f"Source URL: {os.getenv('EXAM_PRICE_URL', PRICE_SOURCE_URL)}")
    print(f"Cache file: {cache_path}")
    print(f"Cache TTL (seconds): {CACHE_TTL_SECONDS}")
    if cache_path.exists():
        print(f"Cache exists: yes (size={cache_path.stat().st_size} bytes, mtime={human_ts(cache_path)})")
    else:
        print("Cache exists: no")

    try:
        await catalog.lookup_price(args.sample, force_refresh=args.force_refresh)
        print("Download/parse: OK")
        if catalog._price_map:
            print(f"Loaded entries: {len(catalog._price_map)}")
            match = catalog._price_map.get(catalog._normalize(args.sample))
            print(f"Sample lookup '{args.sample}': {'found' if match is not None else 'not found'}")
        else:
            print("Catalog empty; using fallback in application paths")
    except Exception as exc:  # noqa: W0703
        print(f"Download/parse failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
