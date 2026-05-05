# Project Overview

## 목적

VoiceGuide는 카메라 기반 장애물 인식, 거리/방향 안내, 음성 입출력을 결합해 시각 보조 안내를 제공하는 프로젝트입니다.

## 핵심 기능

- Android 앱에서 카메라 프레임 수집
- 온디바이스 ONNX YOLO 추론
- 필요 시 서버/GCP 기반 분석 보조
- 장애물, 찾기, 확인 모드별 문장 생성
- STT/TTS 기반 음성 상호작용
- FPS, GPS, 탐지 결과, 위험 문장 검증

## 현재 루트 구조

- `android/`: Android 앱
- `src/`: 서버와 Python 핵심 로직
- `tests/`: 자동 테스트
- `tools/`: 검증/운영 도구
- `templates/`: 서버 UI 템플릿
- `train/`: 학습/데이터 준비 스크립트
- `data/`: 샘플 데이터와 예시 파일
- `depth_anything_v2/`: 깊이 추정 모듈
- `legacy/`: 과거 문서, 실험 코드, 산출물 보관

## 상세 원본

- `legacy/md/PRD.md`
- `legacy/md/PROJECT_STRUCTURE.md`
- `legacy/md/PROJECT_GUIDE.md`
- `legacy/md/TECH.md`
- `legacy/md/mvp_checklist.md`

