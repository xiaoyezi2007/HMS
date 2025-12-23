from __future__ import annotations

import asyncio
import difflib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import httpx
import xlrd

PRICE_SOURCE_URL = os.getenv(
    "EXAM_PRICE_URL",
    "https://ybj.beijing.gov.cn/2020_zwfw/2020_bmcx/202002/P020211231647015053723.xls",
)
CACHE_TTL_SECONDS = int(os.getenv("EXAM_PRICE_CACHE_TTL", "43200"))  # 12 hours
CACHE_FILE = Path(
    os.getenv(
        "EXAM_PRICE_CACHE_PATH",
        Path(__file__).resolve().parent.parent / "data" / "exam_price_catalog.xls",
    )
).resolve()


@dataclass
class PriceLookupResult:
    price: float
    matched_name: str


class ExamPriceCatalog:
    def __init__(self, source_url: str = PRICE_SOURCE_URL):
        self.source_url = source_url
        self.cache_ttl = CACHE_TTL_SECONDS
        self.cache_file = CACHE_FILE
        self._price_map: Dict[str, float] = {}
        self._raw_names: Dict[str, str] = {}
        self._loaded_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _normalize(name: str) -> str:
        text = (name or "").strip().lower()
        if not text:
            return ""
        return re.sub(r"[\s·•、,，.。/\\-]", "", text)

    @staticmethod
    def _parse_price(value) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"[-+]?[0-9]*\.?[0-9]+", value)
            if match:
                try:
                    return float(match.group())
                except ValueError:
                    return None
        return None

    @staticmethod
    def _pick_column(headers: Iterable[str], keywords: Tuple[str, ...]) -> Optional[int]:
        for idx, header in enumerate(headers):
            for kw in keywords:
                if kw in header:
                    return idx
        return None

    def _parse_catalog(self, data: bytes) -> Dict[str, float]:
        workbook = xlrd.open_workbook(file_contents=data)
        sheet = workbook.sheet_by_index(0)
        headers = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
        name_col = self._pick_column(headers, ("项目名称", "医疗服务项目名称", "检查项目", "项目", "名称"))
        price_col = self._pick_column(headers, ("价格", "收费标准", "单价", "收费金额", "金额"))
        if name_col is None or price_col is None:
            raise ValueError("无法在价格表中找到项目名称或价格列")

        mapping: Dict[str, float] = {}
        raw_names: Dict[str, str] = {}
        for row in range(1, sheet.nrows):
            raw_name = str(sheet.cell_value(row, name_col)).strip()
            if not raw_name:
                continue
            price_val = self._parse_price(sheet.cell_value(row, price_col))
            if price_val is None:
                continue
            key = self._normalize(raw_name)
            if not key:
                continue
            mapping[key] = round(float(price_val), 2)
            raw_names[key] = raw_name
        self._price_map = mapping
        self._raw_names = raw_names
        return mapping

    async def _download_latest(self) -> bytes:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Referer": "https://ybj.beijing.gov.cn/",
        }
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            resp = await client.get(self.source_url)
            resp.raise_for_status()
            return resp.content

    async def _ensure_catalog(self, force_refresh: bool = False) -> Dict[str, float]:
        async with self._lock:
            now = datetime.utcnow()
            if (
                not force_refresh
                and self._price_map
                and self._loaded_at
                and now - self._loaded_at < timedelta(seconds=self.cache_ttl)
            ):
                return self._price_map

            data: Optional[bytes] = None
            last_error = None
            try:
                data = await self._download_latest()
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                self.cache_file.write_bytes(data)
            except Exception as exc:  # noqa: W0703
                last_error = exc
                if self.cache_file.exists():
                    data = self.cache_file.read_bytes()
            if data is None:
                # Network/cache both failed; keep app running with empty catalog and let caller use fallback price
                self._price_map = {}
                self._raw_names = {}
                self._loaded_at = now
                print(f"WARN: exam price catalog unavailable: {last_error}")
                return self._price_map

            self._parse_catalog(data)
            self._loaded_at = now
            return self._price_map

    async def lookup_price(self, exam_name: str, force_refresh: bool = False) -> Optional[PriceLookupResult]:
        await self._ensure_catalog(force_refresh=force_refresh)
        normalized = self._normalize(exam_name)
        if not normalized:
            return None

        direct = self._price_map.get(normalized)
        if direct is not None:
            return PriceLookupResult(price=direct, matched_name=self._raw_names.get(normalized, exam_name))

        # substring / containment
        candidate_key = None
        candidate_price = None
        longest = 0
        for key, price in self._price_map.items():
            if key in normalized or normalized in key:
                if len(key) > longest:
                    longest = len(key)
                    candidate_key = key
                    candidate_price = price
        if candidate_price is not None and candidate_key:
            return PriceLookupResult(price=candidate_price, matched_name=self._raw_names.get(candidate_key, candidate_key))

        # fuzzy fallback
        closest = difflib.get_close_matches(normalized, list(self._price_map.keys()), n=1, cutoff=0.8)
        if closest:
            key = closest[0]
            return PriceLookupResult(price=self._price_map[key], matched_name=self._raw_names.get(key, key))
        return None


exam_price_catalog = ExamPriceCatalog()
