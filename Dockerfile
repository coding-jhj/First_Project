# VoiceGuide FastAPI 서버 — Google Cloud Run 배포용 이미지
# 빌드: docker build -t voiceguide-server .
# 실행: docker run -p 8080:8080 --env-file .env voiceguide-server
FROM python:3.10-slim

WORKDIR /app

# FastAPI JSON 라우터 실행에 필요한 최소 시스템 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
# Cloud Run 서버에서 불필요한 모델 준비/학습 도구 제외:
#   torch/torchvision/ultralytics/opencv/numpy/Pillow - Android ONNX 모델 준비용
#   ddgs         - 파인튜닝 데이터 수집 도구
#   onnx/onnxscript - ONNX 내보내기 도구
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    grep -vE "^(torch|torchvision|numpy|ultralytics|opencv-python-headless|Pillow|ddgs|onnx|onnxscript)" \
        requirements.txt > /tmp/requirements-prod.txt && \
    pip install --no-cache-dir -r /tmp/requirements-prod.txt

# 소스 코드 복사
COPY src/ ./src/
COPY templates/ ./templates/

# Cloud Run은 PORT 환경변수를 자동 주입 (기본 8080)
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# 단일 워커: Cloud Run은 인스턴스 수평 확장으로 동시성 처리
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}
