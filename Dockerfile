# VoiceGuide FastAPI 서버 — Google Cloud Run 배포용 이미지
# 빌드: docker build -t voiceguide-server .
# 실행: docker run -p 8080:8080 --env-file .env voiceguide-server
FROM python:3.10-slim

WORKDIR /app

# OpenCV 실행에 필요한 시스템 라이브러리
# libgomp1: YOLO/Torch OpenMP 병렬처리 / libgl1: OpenCV imshow (서버에선 불필요하지만 import에 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
# Cloud Run 서버에서 불필요한 로컬 전용 패키지 제외:
#   pyaudio      - portaudio 시스템 라이브러리 필요 (서버 미사용)
#   pygame       - SDL2 시스템 라이브러리 필요 (서버 미사용)
#   gradio       - 로컬 데모 UI (서버 미사용)
#   huggingface_hub / websockets - gradio 의존성
#   SpeechRecognition - 로컬 STT (서버 미사용)
#   ddgs         - 파인튜닝 데이터 수집 도구 (서버 미사용)
#   easyocr      - 버스 OCR 실험 기능 (서버 미사용)
#   onnxscript   - ONNX 내보내기 도구 (서버 미사용)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    grep -vE "^(pyaudio|pygame|gradio|huggingface_hub|websockets|SpeechRecognition|ddgs|easyocr|onnxscript)" \
        requirements.txt > /tmp/requirements-prod.txt && \
    pip install --no-cache-dir -r /tmp/requirements-prod.txt

# 소스 코드 복사
COPY src/ ./src/
COPY templates/ ./templates/
COPY depth_anything_v2/ ./depth_anything_v2/

# YOLO 커스텀 모델 복사 (yolo26s.pt — ultralytics hub에 없어 자동 다운로드 불가)
COPY yolo26s.pt ./yolo26s.pt

# Depth 모델(99MB)은 git에 없음 → 로컬 실행 시 .env의 DEPTH_ENABLED=1로 자동 사용
# Cloud Run에 포함하려면: docker build 전에 프로젝트 루트에 파일 위치 후
#   docker build --build-arg INCLUDE_DEPTH=1 ... 방식 대신
#   직접 COPY 라인 추가: COPY depth_anything_v2_vits.pth ./
# 파일 없으면 DEPTH_ENABLED=1이어도 bbox fallback으로 자동 전환 (에러 없음)

ARG SERVER_YOLO_MODEL=yolo26s.pt
ENV SERVER_YOLO_MODEL=${SERVER_YOLO_MODEL}

# Cloud Run은 PORT 환경변수를 자동 주입 (기본 8080)
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV DEPTH_ENABLED=1

# 단일 워커: Cloud Run은 인스턴스 수평 확장으로 동시성 처리
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}
