"""
Phase 4용 최소 테스트셋 자동 생성 스크립트.

목표:
  data/test_images/<한국어클래스>/ 에 실제 이미지를 N장씩 채워서
  tools/benchmark.py 의 Precision/Recall/F1/FPR 측정이 바로 돌아가게 만든다.

사용:
  python tools/build_test_images.py

의존:
  - ddgs (DuckDuckGo Search)
  - pillow (일부 이미지 변환)
"""

from __future__ import annotations

import os
import random
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUT_DIR = Path("data/test_images")


@dataclass(frozen=True)
class Target:
    class_ko: str
    queries: list[str]
    n: int


TARGETS: list[Target] = [
    Target("의자", ["indoor chair photo", "chair in room", "office chair"], 12),
    Target("사람", ["person walking street", "person indoor standing", "pedestrian sidewalk"], 12),
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
    """
    다운로드 결과가 '진짜 이미지'인지 빠르게 검증.
    (HTML/오류페이지가 .jpg로 저장되는 경우를 제거)
    """
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
            for item in ddgs.images(q, max_results=max_results):
                url = item.get("image", "")
                if url and url.startswith("http"):
                    urls.append(url)
            time.sleep(0.8)
    random.shuffle(urls)
    # 중복 제거
    seen = set()
    uniq = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
    return uniq


def build_for_target(t: Target) -> dict:
    out = OUT_DIR / t.class_ko
    out.mkdir(parents=True, exist_ok=True)

    # 기존 파일도 유효성 검사해서 깨진 파일(HTML 등) 제거
    existing = list(out.glob("*.jpg")) + list(out.glob("*.jpeg")) + list(out.glob("*.png")) + list(out.glob("*.webp"))
    removed = 0
    for p in existing:
        if p.stat().st_size < 10_000 or not _is_valid_image(p):
            try:
                p.unlink()
                removed += 1
            except Exception:
                pass

    existing = list(out.glob("*.jpg")) + list(out.glob("*.jpeg")) + list(out.glob("*.png")) + list(out.glob("*.webp"))
    if len(existing) >= t.n:
        return {"class_ko": t.class_ko, "downloaded": 0, "removed": removed, "skipped": True, "dir": str(out)}

    needed = t.n - len(existing)
    urls = _collect_urls(t.queries, max_results=max(needed * 5, 60))
    downloaded = 0

    for i, url in enumerate(urls):
        if downloaded >= needed:
            break
        ext = _safe_ext_from_url(url)
        dest = out / f"{t.class_ko}_{int(time.time())}_{i:03d}{ext}"
        if _download(url, dest):
            dest2 = _convert_to_jpg_if_needed(dest)
            # 이미지 유효성 검사 (HTML/깨진 파일 제거)
            if (
                dest2.exists()
                and dest2.stat().st_size > 10_000
                and _is_valid_image(dest2)
            ):
                downloaded += 1
            else:
                try:
                    dest2.unlink(missing_ok=True)  # py>=3.8
                except Exception:
                    pass
        time.sleep(0.1)

    return {"class_ko": t.class_ko, "downloaded": downloaded, "removed": removed, "skipped": False, "dir": str(out)}


def main() -> int:
    print("=" * 60)
    print("Phase 4 테스트 이미지 자동 수집")
    print("=" * 60)
    print(f"- 출력 폴더: {OUT_DIR.resolve()}")
    print(f"- 대상: {', '.join(t.class_ko for t in TARGETS)}")

    results = []
    for t in TARGETS:
        print(f"\n[{t.class_ko}] 수집 시작 (목표 {t.n}장)...")
        r = build_for_target(t)
        results.append(r)
        if r["skipped"]:
            print(f"  - 이미 충분함: {r['dir']}")
        else:
            print(f"  - 다운로드: {r['downloaded']}장 -> {r['dir']}")
        if r.get("removed"):
            print(f"  - 정리: 깨진 파일 {r['removed']}개 삭제")

    print("\n완료. 다음 실행:")
    print("  python tools/benchmark.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

