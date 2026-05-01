"""
빠른 단일 이미지 탐지 확인 스크립트 (개발용)
사용법: python tools/quick_detect.py <이미지경로>
예시:  python tools/quick_detect.py data/test_images/chair/chair_000.jpg
"""
import sys
from pathlib import Path
# 루트 경로를 sys.path에 추가 — tools/ 서브디렉터리에서도 src/ 등 임포트 가능
sys.path.insert(0, str(Path(__file__).parent.parent))

from ultralytics import YOLO
import cv2

model = YOLO("yolo11m.pt")  # 현재 디렉터리의 모델 파일 로드

# 인자 없으면 기본 이미지 사용 (의자 샘플)
img_path = sys.argv[1] if len(sys.argv) > 1 else "data/test_images/chair/chair_000.jpg"
img = cv2.imread(img_path)
if img is None:
    print(f"이미지 로드 실패: {img_path}")
    sys.exit(1)

print(f"이미지 크기: {img.shape}")  # (높이, 너비, 채널) 출력

# conf=0.1: 개발용 낮은 임계값 — 놓치는 것 없이 전부 확인 (실서버는 0.5)
results = model(img, conf=0.1)[0]
print(f"\n탐지된 전체 객체 ({len(results.boxes)}개):")
for box in results.boxes:
    cls_name = model.names[int(box.cls)]  # 클래스 인덱스 → 영어 이름 변환
    conf = float(box.conf)
    print(f"  {cls_name}: confidence={conf:.2f}")
