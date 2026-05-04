"""
data/ocr_bus/images/ 의 각 파일에 대해 OCR을 돌려 labels_seed.csv 를 생성합니다.
expected 열은 **자동 추측**이므로 반드시 육안으로 검수한 뒤 labels.csv 로 옮기세요.

사용:
  python tools/seed_bus_ocr_labels.py
  python tools/seed_bus_ocr_labels.py --write-labels   # 검수 없이 labels.csv 덮어쓰기 (비권장)

검수 후:
  copy data\\ocr_bus\\labels_seed.csv data\\ocr_bus\\labels.csv   (수동 편집 포함)
  python tools/eval_bus_ocr.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--write-labels",
        action="store_true",
        help="labels.csv 를 바로 씀 (기존 정답 덮어씀)",
    )
    args = ap.parse_args()

    root = Path(__file__).parent.parent
    img_dir = root / "data" / "ocr_bus" / "images"
    seed_path = root / "data" / "ocr_bus" / "labels_seed.csv"
    labels_path = root / "data" / "ocr_bus" / "labels.csv"

    if not img_dir.is_dir():
        print(f"이미지 폴더 없음: {img_dir}")
        print("먼저: python tools/build_bus_ocr_dataset.py")
        return 1

    files = sorted(
        list(img_dir.glob("*.jpg"))
        + list(img_dir.glob("*.jpeg"))
        + list(img_dir.glob("*.png"))
        + list(img_dir.glob("*.webp"))
    )
    if not files:
        print("이미지가 없습니다.")
        return 1

    try:
        from src.ocr.bus_ocr import recognize_bus_number
    except ImportError as e:
        print(f"EasyOCR 등 의존성 필요: {e}")
        return 1

    rows: list[dict] = []
    for p in files:
        data = p.read_bytes()
        try:
            pred = recognize_bus_number(data, None)
        except Exception:
            pred = None
        rows.append(
            {
                "file": p.name,
                "expected": pred if pred is not None else "",
                "source": "ocr_auto_seed",
            }
        )

    seed_path.parent.mkdir(parents=True, exist_ok=True)
    with seed_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "expected", "source"])
        w.writeheader()
        w.writerows(rows)

    print(f"작성: {seed_path} ({len(rows)}행)")
    print("→ expected 열을 **반드시** 육안 검수한 뒤 틀린 행을 고치세요.")
    print("→ 검수 완료 후 labels.csv 로 복사하거나 내용을 붙여 넣으세요.")

    if args.write_labels:
        import shutil

        shutil.copyfile(seed_path, labels_path)
        print(f"(옵션) labels.csv 로 복사함: {labels_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
