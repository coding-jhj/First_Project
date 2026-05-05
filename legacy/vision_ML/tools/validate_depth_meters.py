"""
보정 후에도 남는 미터 오차를 숫자로 답하기 위한 검증 스크립트.

각 행은 \"알려진 실거리(truth_m)\"와 한 장의 이미지를 연결합니다.
예측값은 detect_and_depth() 결과에서 **가장 가까운 물체**의 distance_m 을 사용합니다.
탐지가 없으면 이미지 중앙 패치의 깊이(Depth 모델 있을 때) 또는 bbox 추정만 가능합니다.

truth CSV 형식 (UTF-8, 헤더 필수):
  file,truth_m
  shot01.jpg,2.0
  shot02.jpg,3.5

사용 (프로젝트 루트):
  python tools/validate_depth_meters.py --truth-csv data/depth_truth/truth.csv --image-dir data/depth_truth

결과: 콘솔 + results/depth_meter_error.md 누적

DEPTH_SCALE 보정은 먼저 tools/calibrate_depth.py 로 한 뒤 이 스크립트를 실행하면
\"이 테스트셋 기준 MAE ±X m\" 형태로 발표용 문장을 만들 수 있습니다.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _pred_closest_object(image_bytes: bytes) -> tuple[float | None, str]:
    from src.depth.depth import DEPTH_SCALE, _check_model, detect_and_depth, infer_raw_depth_map
    import cv2
    import numpy as np

    objects, _, _ = detect_and_depth(image_bytes)
    if objects:
        # 가장 가까운 물체 = distance_m 최소
        best = min(objects, key=lambda o: float(o.get("distance_m", 99)))
        return float(best["distance_m"]), "closest_detection"

    if _check_model():
        nparr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            raw = infer_raw_depth_map(img)
            if raw is not None:
                h, w = raw.shape
                patch = raw[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]
                med = float(np.median(patch))
                if med > 1e-8:
                    pred_m = float(np.clip(med * DEPTH_SCALE, 0.1, 10.0))
                    return pred_m, "center_depth_patch"

    return None, "none"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth-csv", required=True, type=Path)
    ap.add_argument("--image-dir", required=True, type=Path)
    args = ap.parse_args()

    root = Path(__file__).parent.parent
    out_md = root / "results" / "depth_meter_error.md"

    if not args.truth_csv.is_file():
        print(f"CSV 없음: {args.truth_csv}")
        return 1
    if not args.image_dir.is_dir():
        print(f"이미지 디렉터리 없음: {args.image_dir}")
        return 1

    rows_in: list[tuple[str, float]] = []
    with args.truth_csv.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        fields = r.fieldnames or []
        fn_k = next((k for k in fields if k.lower() in ("file", "filename", "image")), "file")
        tm_k = next((k for k in fields if k.lower() in ("truth_m", "meters", "m", "truth")), "truth_m")
        for row in r:
            fn = (row.get(fn_k) or "").strip()
            if fn.startswith("#"):
                continue
            tm_s = (row.get(tm_k) or "").strip()
            if not fn or not tm_s:
                continue
            try:
                tm = float(tm_s)
            except ValueError:
                continue
            rows_in.append((fn, tm))

    if not rows_in:
        print("유효한 CSV 행이 없습니다.")
        return 1

    errs: list[tuple[str, float, float | None, str]] = []
    for fn, truth in rows_in:
        p = args.image_dir / fn
        if not p.is_file():
            errs.append((fn, truth, None, "missing_file"))
            continue
        pred, src = _pred_closest_object(p.read_bytes())
        errs.append((fn, truth, pred, src))

    usable = [(fn, t, p) for fn, t, p, s in errs if p is not None]
    if not usable:
        print("예측 가능한 행이 없습니다. Depth 모델 또는 탐지 결과를 확인하세요.")
        return 1

    abs_err = [abs(p - t) for _fn, t, p in usable]
    mae = sum(abs_err) / len(abs_err)
    rmse = math.sqrt(sum((p - t) ** 2 for _fn, t, p in usable) / len(usable))
    max_e = max(abs_err)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"""
---

## Depth 미터 오차 검증 — {now}

- 이미지 수: **{len(usable)}** / CSV 행 **{len(rows_in)}**
- **MAE**: {mae:.3f} m  
- **RMSE**: {rmse:.3f} m  
- **최대 절대 오차**: {max_e:.3f} m  

발표용 한 줄 예시:  
「이 캘리브레이션 샷 기준으로 거리 추정 오차는 평균 약 **±{mae:.2f} m** 수준이다.」

### 개별 행
| 파일 | truth(m) | pred(m) | |오차| | 출처 |
|------|----------|---------|------|------|
"""

    for fn, t, p, src in errs:
        if p is None:
            block += f"| `{fn}` | {t} | — | — | {src} |\n"
        else:
            block += f"| `{fn}` | {t} | {p:.2f} | {abs(p-t):.2f} | {src} |\n"

    out_md.parent.mkdir(parents=True, exist_ok=True)
    prev = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
    out_md.write_text(prev + block, encoding="utf-8")

    print(block)
    print(f"기록: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
