"""
yolo11m.pt → ONNX 변환 스크립트
실행: python tools/export_onnx.py  (프로젝트 루트에서)
결과: android/app/src/main/assets/yolo11m.onnx  (두 android 폴더 모두)
"""
import os
import shutil
from pathlib import Path

from ultralytics import YOLO

# 파인튜닝된 실내 특화 모델 우선 사용, 없으면 원본 COCO 모델 사용
_src = "yolo11m_indoor.pt" if os.path.exists("yolo11m_indoor.pt") else "yolo11m.pt"
print(f"내보낼 모델: {_src}")

model = YOLO(_src)
# half=False: Android ONNX Runtime은 FP16 미지원 → FP32 필수
# simplify=True: onnxsim으로 불필요한 노드 제거 → 추론 속도 향상
model.export(format="onnx", imgsz=640, half=False, simplify=True)

src = Path("yolo11m.onnx")  # ultralytics가 현재 디렉터리에 생성한 ONNX 파일

# android 폴더가 두 곳 — 둘 다 업데이트
dst_dirs = [
    Path("android/app/src/main/assets"),                    # c:/VoiceGuide/VoiceGuide/android (신버전)
    Path("../android/app/src/main/assets"),                  # c:/VoiceGuide/android (구버전, 혹시 몰라)
]

for dst_dir in dst_dirs:
    dst_dir.mkdir(parents=True, exist_ok=True)   # 경로 없으면 자동 생성
    dst = dst_dir / "yolo11m.onnx"
    shutil.copy(src, dst)                         # 양쪽 폴더에 동일한 모델 복사
    print(f"완료: {dst.resolve()}  ({dst.stat().st_size / 1024 / 1024:.1f} MB)")
