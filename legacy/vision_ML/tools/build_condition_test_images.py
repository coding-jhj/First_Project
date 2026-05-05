"""
환경(조건)별 소형 테스트셋을 data/test_images_conditions/<조건>/<클래스>/ 에 채웁니다.

benchmark_conditions.py 가 같은 폴더 구조를 읽어 조건별 P/R/F/FPR 을 낸다.

사용:
  python tools/build_condition_test_images.py

의존: ddgs (build_test_images.py 와 동일)
"""

from __future__ import annotations

import os
import random
import time
import urllib.request
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = Path("data/test_images_conditions")

# (조건폴더명, 한글클래스, 장수, 검색어들)
CONDITION_ROWS: list[tuple[str, str, int, list[str]]] = [
    (
        "야간",
        "사람",
        10,
        [
            "person walking at night street photo",
            "pedestrian night city lights",
            "dark street human silhouette photo",
        ],
    ),
    (
        "주간",
        "사람",
        10,
        ["person walking daylight sidewalk", "pedestrian sunny street outdoor photo"],
    ),
    (
        "야간",
        "의자",
        8,
        ["chair in dim room photo", "dark indoor chair furniture"],
    ),
    (
        "주간",
        "의자",
        8,
        ["chair indoor daylight photo", "office chair bright room"],
    ),
]


def _safe_ext_from_url(url: str) -> str:
    u = url.split("?")[0].lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if u.endswith(ext):
            return ext.replace(".jpeg", ".jpg")
    return ".jpg"


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = r.read()
        if len(data) < 10_000:
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def _is_valid_image(p: Path) -> bool:
    try:
        import cv2
        import numpy as np

        raw = p.read_bytes()
        nparr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img is not None and img.size > 0
    except Exception:
        return False


def _convert_to_jpg_if_needed(p: Path) -> Path:
    if p.suffix.lower() in (".jpg", ".jpeg"):
        return p
    try:
        from PIL import Image as PILImage

        img = PILImage.open(p).convert("RGB")
        jpg_path = p.with_suffix(".jpg")
        img.save(jpg_path, "JPEG", quality=90)
        try:
            p.unlink()
        except Exception:
            pass
        return jpg_path
    except Exception:
        return p


def _collect_urls(queries: list[str], max_results: int) -> list[str]:
    from ddgs import DDGS

    urls: list[str] = []
    with DDGS() as ddgs:
        for q in queries:
            try:
                for item in ddgs.images(q, max_results=max_results):
                    url = item.get("image", "")
                    if url and url.startswith("http"):
                        urls.append(url)
                time.sleep(0.75)
            except Exception:
                time.sleep(1.2)
    random.shuffle(urls)
    seen: set[str] = set()
    uniq: list[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
    return uniq


def main() -> int:
    print("조건별 테스트 이미지 수집 →", BASE.resolve())
    BASE.mkdir(parents=True, exist_ok=True)

    for cond, cls_ko, n, queries in CONDITION_ROWS:
        out = BASE / cond / cls_ko
        out.mkdir(parents=True, exist_ok=True)
        have = len([p for p in out.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and _is_valid_image(p)])
        if have >= n:
            print(f"[{cond}/{cls_ko}] 이미 {have}장 — 건너뜀")
            continue
        need = n - have
        urls = _collect_urls(queries, max_results=max(need * 6, 40))
        got = 0
        for i, url in enumerate(urls):
            if got >= need:
                break
            ext = _safe_ext_from_url(url)
            dest = out / f"{cond}_{cls_ko}_{int(time.time())}_{i:03d}{ext}"
            if _download(url, dest):
                dest2 = _convert_to_jpg_if_needed(dest)
                if dest2.exists() and dest2.stat().st_size > 10_000 and _is_valid_image(dest2):
                    got += 1
                else:
                    try:
                        dest2.unlink(missing_ok=True)
                    except Exception:
                        pass
            time.sleep(0.1)
        print(f"[{cond}/{cls_ko}] +{got}장 -> {out}")

    print("\n다음: python tools/benchmark_conditions.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
