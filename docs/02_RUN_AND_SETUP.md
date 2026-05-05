# Run And Setup

## 빠른 실행 요약

Windows 기준 기본 위치는 다음과 같습니다.

```bat
cd /d C:\VoiceGuide\VoiceGuide
```

Python 의존성 설치:

```bat
pip install -r requirements.txt
```

환경 변수 준비:

```bat
copy .env.example .env
```

서버 실행:

```bat
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

테스트 실행:

```bat
python -m pytest
```

## Android 실행

Android Studio에서 여는 폴더는 저장소 루트가 아니라 `android/`입니다.

```text
C:\VoiceGuide\VoiceGuide\android
```

실행 순서:

1. Android Studio 실행
2. `android/` 폴더 열기
3. 휴대폰 USB 연결
4. USB 디버깅 허용
5. Run 버튼으로 설치/실행

Android 앱은 기본적으로 온디바이스 ONNX를 우선 사용합니다. 서버 URL이 없어도 장애물/찾기/확인 흐름은 유지하는 방향이 기준입니다.

## GCP 배포

Cloud Run 배포 예시:

```bat
gcloud run deploy voiceguide --source . --region asia-northeast3 --memory 2Gi --cpu 2 --timeout 120 --allow-unauthenticated --port 8080
```

배포 후 확인:

```bat
python tools\probe_server_link.py --base https://voiceguide-1063164560758.asia-northeast3.run.app
```

## 모델 파일

모델 파일은 용량이 커서 Git에 올리지 않습니다.

| 파일 유형 | 관리 방식 |
|---|---|
| `*.pt`, `*.pth` | 로컬 `models/` 또는 팀 공유 |
| `*.onnx`, `*.onnx.data` | 로컬 `models/`, Android assets |
| Android 내장 모델 | `android/app/src/main/assets/` |

## Git에 올리지 않는 것

- `.env`, `.env.*`
- `models/`
- `voiceguide.db`
- `.pytest_cache/`, `__pycache__/`, `.ultralytics/`
- Android/Gradle 빌드 산출물
- 대용량 학습/실험 산출물

## 발표 전 체크

| 항목 | 확인 |
|---|---|
| 서버 실행 | `/health` 응답 확인 |
| Android 실행 | 앱 설치 후 카메라 권한 확인 |
| 온디바이스 추론 | 서버 없이 기본 안내 가능 여부 확인 |
| TTS | 안내 문장이 겹치지 않는지 확인 |
| 테스트 | `tests/test_sentence.py`, `tests/test_detect.py` 통과 |
