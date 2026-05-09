# 정규화 작업 — 코드 어디를 어떻게 바꾸는지

> 코드를 새로 짜는 게 아니라, 지금 있는 코드에서 **딱 이 부분만** 고치면 됩니다.

---

## 작업 1. "물체 없음"인데 DB에 저장되는 문제 제거

### 지금 어떻게 돼 있나

파일: `src/api/routes.py`, 라인 293~317

```python
should_persist = _should_persist_frame(session_id, objects, mode)  # 293번줄

# 296번줄 — 스냅샷 저장은 objects가 있을 때만 저장 (이건 이미 맞음)
if objects and should_persist:
    db.save_snapshot(wifi_ssid, objects)
    ...

# 303번줄 — 문제! objects가 비어있어도 여기 들어옴
if should_persist:
    db_enqueued = db.enqueue_detection_event(
        ...
        objects=objects,   # 빈 리스트 []가 저장됨
        ...
    )
```

**문제:** `_should_persist_frame()` 함수는 "N번째 프레임마다" 라는 규칙으로 True를 반환합니다.  
카메라가 빈 공간을 찍어서 아무것도 없어도, 5번째 프레임이라는 이유만으로 `should_persist = True`가 됩니다.  
그래서 빈 이벤트가 DB에 계속 쌓입니다.

### 고치는 방법

303번 줄의 조건을 이렇게 바꿉니다:

```python
# 변경 전
if should_persist:

# 변경 후
if should_persist and objects:
```

**딱 한 단어 추가 (`and objects`)입니다.**

이렇게 하면:
- 물체 O + 저장 타이밍 O → 저장됨 ✅
- 물체 X + 저장 타이밍 O → 저장 안 됨 ✅ (고쳐지는 부분)
- 물체 O + 저장 타이밍 X → 저장 안 됨 (원래도 안 됐음)

---

## 작업 2. GPS 위치 → 시뮬레이터 동선으로 바꾸기

### 왜 바꾸는가

지금은 안드로이드 앱이 실제 GPS 좌표를 서버에 보냅니다.  
이걸 그대로 쓰면 실제 이동 경로(개인정보)가 서버에 저장됩니다.

대신, **미리 짜둔 경로를 파이썬 스크립트가 서버에 보내는 방식**으로 바꿉니다.  
앱은 GPS를 그냥 안 보내도 됩니다 (lat=0, lng=0).

### 어디에 파일을 만드나

새 파일: `tools/simulator.py` (기존 파일 수정 없음)

### 시뮬레이터 코드 구조

```python
"""
demo_simulator.py
대시보드 데모용 GPS 동선 시뮬레이터.
실제 GPS 대신 미리 정해진 경로를 서버에 전송합니다.
"""
import time
import requests

SERVER_URL = "https://[서버주소]"  # GCP 서버 주소로 변경
SESSION_ID = "demo-device-01"      # 대시보드에서 이 ID로 세션 선택
API_KEY    = "your-api-key"        # .env의 API_KEY 값

# 미리 짜둔 경로 (위도, 경도)
# 예시: 건물 입구 → 1층 복도 → 계단 → 2층
ROUTE = [
    (37.5000, 127.0000),   # 건물 입구
    (37.5001, 127.0001),   # 복도 시작
    (37.5002, 127.0002),   # 복도 중간
    (37.5003, 127.0003),   # 계단 앞
    (37.5004, 127.0004),   # 계단 위
    (37.5005, 127.0005),   # 2층 도착
]

HEADERS = {"X-Api-Key": API_KEY}
INTERVAL = 2.0  # 2초마다 다음 좌표로 이동

for lat, lng in ROUTE:
    resp = requests.post(
        f"{SERVER_URL}/gps",
        data={
            "device_id": SESSION_ID,
            "lat": lat,
            "lng": lng,
        },
        headers=HEADERS,
    )
    print(f"GPS 전송: {lat}, {lng} → {resp.status_code}")
    time.sleep(INTERVAL)

print("시뮬레이션 완료")
```

### 실행 방법

```bash
# 터미널에서
python tools/simulator.py
```

대시보드에서 세션 ID를 `demo-device-01`로 입력하면  
지도에 이동 경로가 실시간으로 그려집니다.

### 안드로이드 앱은 어떻게 하나

앱은 GPS 전송을 끄거나, 그냥 아무 좌표나 보내도 됩니다.  
시뮬레이터가 별도 세션 ID(`demo-device-01`)로 GPS를 보내기 때문에  
앱과 시뮬레이터 세션이 섞이지 않습니다.

---

## 작업 3. DB에 뭘 왜 저장하는지 정리

### 현재 저장 중인 테이블들

| 테이블 | 저장 내용 | 누가 저장 | 왜 필요한가 |
|--------|-----------|-----------|-------------|
| `detection_events` | 탐지 이벤트 전체 (raw_json 포함) | `/detect` 호출마다 | 24시간 내역 대시보드에 사용 |
| `detections` | 개별 물체 행 | 위와 동일 | 질문 응답, tracker 복원 |
| `gps_history` | GPS 좌표 이력 | `/gps` 또는 `/detect` | 지도 경로 그리기 |
| `snapshots` | 공간별 마지막 물체 상태 | 위와 동일 | "방금 전 뭐 있었지?" 비교용 |
| `saved_locations` | 사용자가 저장한 장소 이름 | 앱 장소 저장 기능 | 찾기 기능에서 사용 |

### 정리가 필요한 부분: `raw_json` 저장

파일: `src/api/db.py`, 라인 376~432 (`save_detection_event` 함수)

지금 `raw_json` 컬럼에 앱이 보낸 **원본 JSON 전체**가 저장됩니다.  
이건 디버깅 목적인데, 데모에는 필요 없고 DB 용량만 차지합니다.

**선택지 A: 일단 놔두기 (권장)**
- 포트폴리오에서 "원본 데이터까지 저장한다"고 설명 가능
- 삭제하면 나중에 디버깅이 어려워짐

**선택지 B: 빈 값으로 대체**  
`save_detection_event` 함수 393번 줄 근처:
```python
# 변경 전
raw_json = json.dumps(raw_payload, ensure_ascii=False)

# 변경 후
raw_json = "{}"  # raw 저장 안 함
```

### 결론

지금 있는 저장 구조는 나름 이유가 있습니다.  
`raw_json`만 필요 없고, 나머지는 기능에 직접 연결돼 있습니다.  
**작업 1 (`and objects`)만 해도 가장 눈에 띄는 문제는 해결됩니다.**

---

## 작업 4. GCP 서버를 VS Code에 연결하기

### Remote SSH 연결 설정

**1단계: VS Code에 확장 설치**
- VS Code 확장에서 "Remote - SSH" 검색 후 설치

**2단계: SSH config 파일 작성**  
파일 위치: `C:\Users\[사용자이름]\.ssh\config`

```
Host voiceguide-gcp
    HostName [GCP 외부 IP]
    User [GCP 사용자명]
    IdentityFile C:\Users\[사용자이름]\.ssh\google_compute_engine
```

**3단계: VS Code에서 연결**
- 좌하단 `><` 버튼 클릭 → "Connect to Host" → `voiceguide-gcp` 선택
- 서버 파일을 직접 열고 수정 가능

**4단계: 서버에서 바로 Python 실행**
- VS Code 터미널에서 `cd /app` (또는 서버 앱 경로)
- `uvicorn src.api.main:app --reload` 실행
- 코드 저장 시 서버 자동 재시작

---

## 작업 5. 대시보드 데모 시나리오 (코드 변경 없음)

### 발표 순서

```
1. 브라우저에서 대시보드 열기
   → 세션 ID 입력: "demo-device-01"
   → "연결됨" 표시 확인

2. 터미널에서 시뮬레이터 실행
   → python tools/simulator.py
   → 지도에 점이 찍히기 시작

3. 안드로이드 앱 실행
   → 사람/의자/자전거 등 물체 비추기
   → 왼쪽 패널에 탐지된 물체 실시간 표시
   → 위험/주의/안전 수치 변동

4. 24시간 내역 패널 보여주기
   → "오늘 하루 몇 번 위험 상황이 있었는지" 설명
```

### 설명 문구 (3문장 버전)

> "시각장애인이 이동하면서 앱이 카메라로 장애물을 감지합니다.  
> 감지 결과는 서버로 전송되고, 대시보드에서 실시간으로 확인할 수 있습니다.  
> 보호자나 관리자가 이동 경로와 위험 상황을 모니터링할 수 있습니다."

---

## 요약: 건드려야 할 파일

| 파일 | 변경 내용 | 난이도 |
|------|-----------|--------|
| `src/api/routes.py` 303번 줄 | `if should_persist:` → `if should_persist and objects:` | 쉬움 (한 줄) |
| `tools/simulator.py` | 새 파일 생성 (GPS 시뮬레이터) | 보통 |
| `C:\Users\...\.ssh\config` | GCP SSH 연결 설정 | 쉬움 |

**건드리지 않아도 되는 것:**
- `db.py` (저장 구조 자체는 OK)
- `dashboard.html` (화면 구조 OK)
- 안드로이드 코드 (시뮬레이터가 대신함)
- 모든 NLG/모델 관련 코드
