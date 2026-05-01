# Server Role Guide

현재 서버 담당은 정환주입니다. 임명광은 NLG 응답 문장과 문서 보조를 맡고, 신유득은 Vision/ML 결과가 서버 응답에 잘 들어가는지 검증합니다.

## 책임 구분

| 담당 | 책임 |
|---|---|
| 정환주 | `src/api/`, GCP Cloud Run, `/dashboard`, README 서버 설명 |
| 임명광 | `src/nlg/`, 서버 응답 문장, alert mode 설명 |
| 신유득 | `src/vision/`, `src/depth/`, `src/ocr/` 결과 검증 |
| 김재현 | Android `sendToServer()`와 온디바이스 fallback |
| 문수찬 | Voice fallback과 Q&A |

## 서버에서 꼭 설명할 것

1. 본 서버는 `src.api.main:app` 하나다.
2. `/detect`는 `src/api/routes.py`에 있다.
3. GCP Cloud Run이 주 배포 경로다.
4. 서버가 실패해도 Android 온디바이스 fallback이 있다.
5. 거리와 계단 감지는 보조/실험 범위를 과장하지 않는다.

## 실행 확인

```bat
python tools\probe_server_link.py --base https://voiceguide-135456731041.asia-northeast3.run.app
```

성공 기준:

```text
/health OK
/dashboard OK
/detect OK 또는 안전한 fallback 응답
```
