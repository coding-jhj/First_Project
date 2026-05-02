"""
실사에 가까운 버스 전면·노선표 이미지를 웹에서 모아 data/ocr_bus/images/ 에 저장합니다.

의존: ddgs, pillow, opencv (build_test_images.py 와 동일)

사용 (프로젝트 루트):
  python tools/build_bus_ocr_dataset.py
  python tools/build_bus_ocr_dataset.py --target 24

다음 단계:
  python tools/seed_bus_ocr_labels.py
  # labels_seed.csv 검수 후 labels.csv 로 반영
  python tools/eval_bus_ocr.py
"""

from __future__ import annotations

import argparse
import os
import random
import time
import urllib.request
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
IMG_DIR = Path("data/ocr_bus/images")

# 노선 번호가 보일 가능성이 있는 검색어 (지역·저작권은 사용자 책임 하에 교체 가능)
BUS_QUERIES = [
    "korean city bus route number display LED",
    "seoul bus front electronic route sign",
    "korea bus destination board night",
    "city bus line number display front Korea",
    "버스 전면 노선번호 전광판",
    "bus LED route number close up",
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
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 8_000:
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
                time.sleep(0.9)
            except Exception:
                time.sleep(1.5)
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
    ap = argparse.ArgumentParser(description="버스 OCR용 이미지 자동 수집")
    ap.add_argument("--target", type=int, default=24, help="목표 장수 (가이드 권장 ~20+)")
    args = ap.parse_args()

    IMG_DIR.mkdir(parents=True, exist_ok=True)

    existing = (
        list(IMG_DIR.glob("*.jpg"))
        + list(IMG_DIR.glob("*.jpeg"))
        + list(IMG_DIR.glob("*.png"))
        + list(IMG_DIR.glob("*.webp"))
    )
    valid_existing = [p for p in existing if p.stat().st_size >= 8_000 and _is_valid_image(p)]
    if len(valid_existing) >= args.target:
        print(f"이미 {len(valid_existing)}장 이상 있습니다: {IMG_DIR.resolve()}")
        print("추가 수집이 필요하면 일부 파일을 옮기거나 --target 을 늘리세요.")
        return 0

    needed = args.target - len(valid_existing)
    print(f"수집 목표: {needed}장 (기존 유효 {len(valid_existing)}장)")
    urls = _collect_urls(BUS_QUERIES, max_results=max(needed * 8, 80))

    ok = 0
    for i, url in enumerate(urls):
        if ok >= needed:
            break
        ext = _safe_ext_from_url(url)
        dest = IMG_DIR / f"bus_ocr_{int(time.time())}_{i:04d}{ext}"
        if _download(url, dest):
            dest2 = _convert_to_jpg_if_needed(dest)
            if dest2.exists() and dest2.stat().st_size >= 8_000 and _is_valid_image(dest2):
                ok += 1
            else:
                try:
                    dest2.unlink(missing_ok=True)
                except Exception:
                    pass
        time.sleep(0.12)

    print(f"완료: 새로 저장 {ok}장 -> {IMG_DIR.resolve()}")
    print("다음: python tools/seed_bus_ocr_labels.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
