# Server Link Check 2026-04-30

담당: 정환주  
로그 공유: 임명광

## 결론

GCP 서버 엔드포인트는 살아 있습니다. 다만 대시보드에 보일 세션 데이터가 아직 비어 있어 화면에는 별도 객체/GPS가 표시되지 않을 수 있습니다.

## 확인한 서버 URL

```text
https://voiceguide-135456731041.asia-northeast3.run.app
```

Android 앱에는 마지막 `/` 없이 아래처럼 입력합니다.

```text
https://voiceguide-135456731041.asia-northeast3.run.app
```

## 임명광 공유 로그 기준

| 로그 | 확인 내용 |
|---|---|
| GCP request log | `GET /status/__default__` 200 OK |
| GCP stdout | `GET /status/__default__ HTTP/1.1` 200 OK |
| Android Logcat | `route=on_device`, 사람 1개 탐지, 문장 생성, 음성 출력 |
| Android Logcat | `1.4fps`, `total=712ms`로 FPS 낮음 |

주의: 공유된 Logcat 프레임은 `route=on_device`입니다. 즉 해당 프레임은 서버 `/detect`가 아니라 Android 온디바이스 경로로 처리되었습니다. 앱과 서버의 완전한 `/detect` 연동 증명에는 `VG_LINK` 로그 또는 GCP `[LINK] request_id=and-...` 로그가 추가로 필요합니다.

## 정환주 서버 담당 확인

| 엔드포인트 | 결과 | 의미 |
|---|---|---|
| `/health` | 200 OK | 서버 정상, DB 정상, Depth는 bbox fallback |
| `/status/__default__` | 200 OK | status API 정상 |
| `/dashboard` | 200 OK | 대시보드 HTML 정상 반환 |

`/status/__default__` 응답:

```json
{
  "session_id": "__default__",
  "objects": [],
  "gps": null,
  "track": []
}
```

## 대시보드가 비어 보이는 이유

대시보드는 `/status/{session_id}`를 폴링합니다. 현재 `__default__` 세션에는 객체, GPS, 이동 경로가 없습니다.

가능한 원인:

1. Android가 온디바이스 경로만 사용해서 서버 `/detect`로 객체를 보내지 않았다.
2. Android가 보낸 `wifi_ssid`와 대시보드 입력 세션 ID가 다르다.
3. GPS 권한 또는 위치값이 없어 `gps`와 `track`이 저장되지 않았다.
4. `/detect` 요청은 있었지만 `lat=0`, `lng=0`이라 GPS 저장이 생략됐다.

## 다음 확인 순서

1. Android Logcat에서 `VG_LINK`를 확인한다.
2. GCP 로그에서 같은 `request_id=and-...`의 `[LINK] START`와 `[PERF]`를 찾는다.
3. 대시보드 세션 입력값을 Android의 `wifi_ssid`와 맞춘다.
4. GPS 권한을 켜고 `/detect` 요청에 `lat/lng`가 들어가는지 본다.
5. `/status/{wifi_ssid}` 응답의 `objects`, `gps`, `track`이 채워지는지 확인한다.
