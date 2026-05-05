# Server And GCP

## 서버 역할

서버는 Android 앱에서 넘어온 이미지와 메타데이터를 받아 탐지, 문장 생성, 음성 기능, 위치/상태 저장을 처리합니다.

주요 관심사는 다음과 같습니다.

- `/detect` 분석 요청 처리
- `/tts` 음성 합성
- 위치 저장/조회 API
- GCP 배포 환경과 로컬 환경 분리
- 서버/Android 문장 규칙 일치

## GCP 운영 체크포인트

- 배포 전 `requirements.txt`와 `Dockerfile` 확인
- 로컬 전용 패키지/파일이 Cloud Run 빌드에 섞이지 않게 관리
- `.env`와 실제 비밀값은 Git에 올리지 않음
- 서버 로그에서 요청 지연, 탐지 실패, TTS 실패를 우선 확인

## 상세 원본

- `legacy/md/SERVER_GUIDE.md`
- `legacy/md/SERVER_ARCHITECTURE.md`
- `legacy/md/SERVER_ROLE_GUIDE.md`
- `legacy/md/GCP_GUIDE.md`
- `legacy/md/GCP_SERVER_SETUP.md`
- `legacy/md/DEPLOY_GUIDE.md`

