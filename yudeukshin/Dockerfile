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

# Python 의존성 설치 (서버 전용 — gradio·pygame 등 데모 의존성 제외)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-docker.txt

# 소스 코드 복사 (모델 파일·학습 데이터는 .dockerignore로 제외)
COPY src/ ./src/
COPY templates/ ./templates/

# YOLO 모델 빌드 시 미리 다운로드 (첫 요청 지연 방지)
# 없으면 첫 요청 시 ultralytics가 자동 다운로드
RUN python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')" 2>/dev/null || echo "YOLO model will be downloaded on first request"

# Depth 모델은 크기(99MB)로 인해 제외 → bbox fallback 사용
# 모델이 필요하면 Cloud Run에서 GCS 마운트 또는 COPY 추가

# Cloud Run은 PORT 환경변수를 자동 주입 (기본 8080)
# 로그가 버퍼 없이 즉시 Cloud Logging에 출력됨
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV DEPTH_ENABLED=0

# 단일 워커: Cloud Run은 인스턴스 수평 확장으로 동시성 처리
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}
