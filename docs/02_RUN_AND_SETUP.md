# Run And Setup

## 기본 실행 순서

1. Python 의존성 설치

```bash
pip install -r requirements.txt
```

2. 환경 변수 파일 준비

```bash
copy .env.example .env
```

3. 서버 실행

```bash
python app.py
```

4. 테스트 실행

```bash
python -m pytest
```

## 운영 메모

- `requirements-phase4.txt`는 `requirements.txt`로 통합했습니다.
- 모델 파일은 Git에 올리지 않고 로컬 `models/` 또는 Android assets에 둡니다.
- `.env`, DB, 캐시, 빌드 산출물은 `.gitignore` 대상입니다.

## 상세 원본

- `legacy/md/SETUP.md`
- `legacy/md/CMD_RUNBOOK.md`
- `legacy/cloud_smoke_test.py`

