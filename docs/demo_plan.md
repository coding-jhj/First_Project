# 데모 영상 제작 계획

## 목표

파이썬 클라이언트가 GPS 경로 + 탐지 더미 데이터를 실시간으로 서버에 전송하고,  
대시보드에서 실시간 탐지 현황·지도 경로·24시간 내역이 자연스럽게 나타나는 영상 제작.

---

## 전체 흐름

```
demo_simulator.py
  ├─ 시리얼 넘버 고정 (DEMO_SERIAL = "VG-DEMO-001")
  ├─ GPS 경로 포인트 순서대로 순회
  │     └─ POST /gps  (2초 간격)         → 대시보드 지도에 경로 실시간 표시
  └─ 탐지 시나리오 순서대로 순회
        └─ POST /detect (2~3초 간격)     → 실시간 탐지 현황 · 24시간 내역 갱신
```

---

## 기존 tools/simulator.py와 차이점

| 항목 | 기존 simulator.py | 이번 demo_simulator.py |
|---|---|---|
| 전송 데이터 | GPS만 전송 | GPS + 탐지 데이터 함께 전송 |
| 시나리오 | 경로 재생만 | 경로 + 상황별 탐지 시나리오 |
| 시리얼 넘버 | 없음 | DEMO_SERIAL 필드 추가 |
| 목적 | 서버 점검용 | 데모 영상 촬영용 |

---

## 시리얼 넘버

`device_id`에 시리얼 넘버를 포함시켜 구분.  
별도 필드를 추가하면 서버 코드 수정이 필요하므로, 기존 `device_id` 규칙 안에서 처리.

```python
DEMO_SERIAL  = "VG-DEMO-001"          # 기기 시리얼 넘버
SESSION_ID   = f"demo-{DEMO_SERIAL}"  # → "demo-VG-DEMO-001"
WIFI_SSID    = "demo_wifi"            # 세션 정규화에 사용
```

`_normalize_session_id(wifi_ssid=WIFI_SSID, device_id=SESSION_ID)` 결과가 서버 세션 키가 됨.  
대시보드 접속 시 이 세션 ID를 입력하면 해당 기기 데이터만 표시됨.

---

## GPS 경로 더미 데이터

기존 simulator.py의 창동역 경로를 그대로 활용하거나, 촬영 장소에 맞게 좌표 변경.

```python
ROUTE = [
    (37.6534, 127.0436, "출발: 아파트 입구"),
    (37.6532, 127.0439, "골목 진입"),
    (37.6529, 127.0443, "횡단보도 앞"),
    (37.6526, 127.0447, "버스정류장"),
    (37.6522, 127.0451, "도착: 창동역"),
]
```

전송 방식: `POST /gps` — `{ device_id, lat, lng }` 2초 간격

---

## 탐지 시나리오 더미 데이터

경로 진행과 맞물려 상황별로 탐지 데이터를 전송.  
각 시나리오는 `POST /detect`로 전송.

### 시나리오 예시

```python
SCENARIOS = [
    # (전송 시점 설명, objects 리스트)
    ("평상시 보행",
     [
         {"class_ko": "사람", "confidence": 0.91,
          "bbox_norm_xywh": [0.5, 0.5, 0.08, 0.2],
          "distance_m": 6.0, "risk_score": 0.2,
          "is_vehicle": False, "is_animal": False},
     ]),

    ("의자 주의",
     [
         {"class_ko": "의자", "confidence": 0.88,
          "bbox_norm_xywh": [0.45, 0.55, 0.12, 0.18],
          "distance_m": 2.5, "risk_score": 0.52,
          "is_vehicle": False, "is_animal": False},
     ]),

    ("자동차 위험",
     [
         {"class_ko": "자동차", "confidence": 0.95,
          "bbox_norm_xywh": [0.5, 0.4, 0.25, 0.3],
          "distance_m": 4.0, "risk_score": 0.78,
          "is_vehicle": True, "is_animal": False},
     ]),

    ("복합 상황 — 사람+자전거",
     [
         {"class_ko": "사람", "confidence": 0.90,
          "bbox_norm_xywh": [0.3, 0.5, 0.08, 0.2],
          "distance_m": 3.0, "risk_score": 0.55,
          "is_vehicle": False, "is_animal": False},
         {"class_ko": "자전거", "confidence": 0.85,
          "bbox_norm_xywh": [0.65, 0.5, 0.15, 0.22],
          "distance_m": 5.0, "risk_score": 0.40,
          "is_vehicle": True, "is_animal": False},
     ]),

    ("안전 구간",
     []),
]
```

---

## /detect 요청 본문 구조

```python
payload = {
    "device_id":          SESSION_ID,
    "wifi_ssid":          WIFI_SSID,
    "event_id":           f"{SESSION_ID}-{seq:04d}",   # 시리얼 넘버 역할
    "request_id":         f"{SESSION_ID}-{seq:04d}",
    "mode":               "장애물",
    "camera_orientation": "front",
    "lat":                current_lat,
    "lng":                current_lng,
    "objects":            scenario_objects,
    "client_perf":        {"infer_ms": 18, "dedup_ms": 1},
}
```

`seq`는 전송할 때마다 1씩 증가하는 시퀀스 번호 → 순서 추적 가능.

---

## 실행 순서

```
1. 서버 실행 확인
   uvicorn src.api.main:app --host 0.0.0.0 --port 8080

2. 브라우저에서 대시보드 열기
   http://localhost:8080/dashboard
   → 세션 ID 입력: demo-VG-DEMO-001

3. demo_simulator.py 실행
   python tools/demo_simulator.py

4. 대시보드 화면 캡처 시작
   - 지도에 경로가 그려지는 장면
   - 실시간 탐지 현황 카드 변화
   - 24시간 내역 누적
   - 자동차 탐지 시 위험 뱃지 표시
```

---

## 대시보드에서 보이는 항목 체크리스트

| 항목 | 확인 방법 |
|---|---|
| 지도 위 실시간 경로 (파란 선) | GPS 전송마다 연장됨 |
| 현재 위치 마커 | GPS 좌표 따라 이동 |
| 실시간 탐지 카드 | 시나리오 바뀔 때마다 갱신 |
| 위험/주의/안전 카운트 | 시나리오 내 objects 위험도 반영 |
| 24시간 탐지 내역 | 전송 건별 누적 |
| 세션 ID 확인 | `demo-VG-DEMO-001` |

---

## 파일 위치

새로 만들 파일: `tools/demo_simulator.py`  
기존 파일 참고: `tools/simulator.py` (GPS 전송 로직 재사용)
