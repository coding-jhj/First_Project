# 설치 후 이 파일을 실행해서 확인해
# 사용법: python tools/verify.py

import sys
from pathlib import Path
# tools/ 에서 실행해도 루트 패키지를 찾을 수 있도록 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

# (라이브러리명, 권장버전) — "OK"는 권장버전 포함 여부, 다르면 "WARN"
libs = [
    ("torch",              "2.4.1"),
    ("numpy",              "1.26.4"),
    ("ultralytics",        "8.3.2"),
    ("cv2",                "4.10.0"),
    ("gradio",             "4.44.1"),
    ("fastapi",            "0.115.5"),
    ("speech_recognition", "3.10.4"),
    ("gtts",               "2.5.3"),
]

print(f"Python: {sys.version}\n")

for lib_name, expected in libs:
    try:
        lib = __import__(lib_name)
        # __version__ 없는 라이브러리(cv2 등)는 .version 속성 시도
        version = getattr(lib, "__version__",
                  getattr(lib, "version", "확인불가"))
        status = "OK  " if expected in str(version) else "WARN"  # 버전 문자열 포함 여부로 판단
        print(f"{status}  {lib_name}: {version} (권장: {expected})")
    except ImportError:
        print(f"FAIL  {lib_name}: 설치 안됨!")

# torch와 numpy 간 배열 변환 호환성 테스트 (버전 불일치 시 TypeError 발생)
try:
    import torch
    import numpy as np
    t = torch.tensor(np.array([1.0, 2.0]))
    print(f"\ntorch + numpy 호환성: OK ({t})")
except Exception as e:
    print(f"\ntorch + numpy 호환성: FAIL → {e}")

# OpenCV와 numpy 간 이미지 변환 호환성 테스트
try:
    import cv2
    import numpy as np
    img = np.zeros((100, 100, 3), dtype=np.uint8)  # 검정 이미지 생성
    cv2.cvtColor(img, cv2.COLOR_BGR2RGB)            # BGR → RGB 변환 시도
    print("opencv + numpy 호환성: OK")
except Exception as e:
    print(f"opencv + numpy 호환성: FAIL → {e}")
