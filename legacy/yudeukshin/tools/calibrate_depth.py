"""
Depth Anything V2 상대깊이 → 미터 근사용 DEPTH_SCALE 추정.

사용법 (프로젝트 루트):
  python tools/calibrate_depth.py --image path/to.jpg --known-meters 2.0

알려진 실거리의 물체(예: 벽까지 레이저 거리계 2m)를 프레임 중앙에 두고 촬영한 뒤,
해당 영역의 상대깊이 중앙값으로 DEPTH_SCALE = known_m / median(raw) 를 계산합니다.

src/depth/depth.py 의 DEPTH_SCALE 상수에 반영하세요.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser(description="DEPTH_SCALE 보정 도우미")
    ap.add_argument("--image", required=True, help="보정용 이미지 경로")
    ap.add_argument(
        "--known-meters",
        type=float,
        required=True,
        help="해당 물체/면까지의 실제 거리(m)",
    )
    ap.add_argument(
        "--x1", type=float, default=None,
        help="샘플 사각형 좌상단 x (픽셀). 미지정 시 이미지 중앙 40%% 박스",
    )
    ap.add_argument("--y1", type=float, default=None)
    ap.add_argument("--x2", type=float, default=None)
    ap.add_argument("--y2", type=float, default=None)
    args = ap.parse_args()

    from src.depth.depth import (
        DEPTH_SCALE,
        _check_model,
        infer_raw_depth_map,
    )

    if not _check_model():
        print("오류: depth_anything_v2_vits.pth 가 프로젝트 루트에 없습니다.")
        return 1

    raw_path = Path(args.image)
    buf = raw_path.read_bytes()
    arr = np.frombuffer(buf, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        print(f"오류: 이미지를 읽을 수 없습니다: {args.image}")
        return 1

    raw_map = infer_raw_depth_map(img)
    if raw_map is None:
        print("오류: 깊이 추론 실패")
        return 1

    h, w = raw_map.shape
    if args.x1 is not None and args.y1 is not None and args.x2 is not None and args.y2 is not None:
        x1, y1 = int(args.x1), int(args.y1)
        x2, y2 = int(args.x2), int(args.y2)
    else:
        mx, my = w // 2, h // 2
        rw, rh = int(w * 0.4), int(h * 0.4)
        x1, y1 = max(0, mx - rw // 2), max(0, my - rh // 2)
        x2, y2 = min(w, mx + rw // 2), min(h, my + rh // 2)

    patch = raw_map[y1:y2, x1:x2]
    if patch.size == 0:
        print("오류: 샘플 영역이 비었습니다.")
        return 1

    median_raw = float(np.median(patch))
    if median_raw <= 1e-8:
        print("오류: median(raw) 가 너무 작습니다.")
        return 1

    suggested = args.known_meters / median_raw
    print()
    print("── Depth 보정 결과 ──")
    print(f"  샘플 박스 (픽셀): ({x1},{y1}) ~ ({x2},{y2})")
    print(f"  median(raw)      : {median_raw:.6f}")
    print(f"  알려진 거리 (m)  : {args.known_meters}")
    print(f"  제안 DEPTH_SCALE : {suggested:.6f}  (현재 코드값: {DEPTH_SCALE})")
    print()
    print("  src/depth/depth.py 의 DEPTH_SCALE 을 위 값으로 바꾼 뒤,")
    print("  같은 장면에서 distance_m 이 체감과 비슷한지 확인하세요.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
