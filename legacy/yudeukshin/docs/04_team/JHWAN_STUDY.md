# 정환주 역할 조사 정리

> 발표 Q&A 대비용. 강사님이 물어볼 수 있는 질문과 우리 코드 기준 답변.  
> 기준: ROLE_GUIDE.md의 "조사할 자료" 5개 항목 전체 정리.

---

## 1. Cloud Run 배포 로그 확인 방법

### 핵심 한 줄
> **gcloud logging 명령어로 서비스 이름 필터링해서 보거나, Cloud Console에서 Logging 탭으로 확인한다.**

### 방법

```bat
:: 실시간 로그 스트리밍
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=voiceguide"

:: 최근 50줄 조회
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=voiceguide" --limit=50 --format="value(textPayload)"

:: 에러만 필터
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20
```

브라우저: GCP Console → Logging → 서비스 `voiceguide` 선택

### 우리 서버에서 찾을 로그 패턴

| 로그 | 의미 |
|---|---|
| `[DB] 초기화 완료 (PostgreSQL/Supabase)` | 서버 정상 시작 |
| `[YOLO] 모델 로드: yolo11m.pt` | YOLO 워밍업 완료 |
| `[Depth V2] 모델 로드 완료` | Depth 워밍업 완료 |
| `[LINK] request_id=... START` | Android 요청 수신 |
| `[PERF] detect=...ms \| TOTAL=...ms` | 처리 성능 로그 |

`main.py`의 `lifespan`에서 서버 시작 로그가 찍히고, `routes.py`의 `_with_perf()`에서 요청마다 `[LINK]`, `[PERF]` 로그가 남는다.

### 강사님 질문 예상 답변

> "서버 장애 났을 때 어떻게 확인해요?"  
→ `gcloud logging read`로 스택트레이스 확인. `/health` 엔드포인트 호출하면 DB 연결 상태와 Depth 모델 로드 여부가 바로 나옵니다. `global_exception_handler`가 있어서 에러가 나도 Android에는 음성 안내 문장이 반환됩니다.

> "배포 후 어떻게 동작 확인해요?"  
→ `python tools/probe_server_link.py --base https://voiceguide-1063164560758.asia-northeast3.run.app` 실행하면 `/health`, `/detect`, `/status`, `/dashboard` 전부 자동 체크합니다.

---

## 2. FastAPI 예외 처리와 dependency 기반 API Key 인증

### 핵심 한 줄
> **`Depends()`는 라우터 함수 실행 전에 자동 호출되는 공통 처리 함수다. 예외 핸들러는 어떤 오류가 나도 안전한 응답을 보장한다.**

### Dependency 인증 원리

```python
# routes.py — 실제 코드
def _verify_api_key(
    authorization: str = Header(default=""),
    x_api_key: str = Header(default=""),
) -> None:
    if not _API_KEY:
        return          # API_KEY 미설정 = 개발 모드, 인증 생략
    if authorization == f"Bearer {_API_KEY}" or x_api_key == _API_KEY:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")

# detect 함수 실행 전에 _verify_api_key가 자동 실행됨
@router.post("/detect", dependencies=[Depends(_verify_api_key)])
async def detect(...):
    ...
```

**Depends() 동작 순서:**
1. POST /detect 요청 수신
2. FastAPI가 `_verify_api_key()` **자동** 호출
3. 통과하면 `detect()` 실행, 401이면 `detect()` 실행 안 됨

**환경변수로 관리하는 이유:**  
API_KEY를 코드에 직접 쓰면 GitHub에 올라갈 위험이 있음. `.env` 파일에 넣고 `.gitignore`에 추가해서 관리. Cloud Run에서는 환경변수로 주입.

### 예외 처리 원리

```python
# main.py — 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "sentence": "분석 중 오류가 발생했어요. 주의해서 이동하세요.",
            ...
        }
    )
```

**왜 이렇게 했나:**  
시각장애인 안전 앱이라 서버 오류가 나도 Android TTS가 아무 말도 안 하면 안 됨. 오류가 나면 "주의해서 이동하세요"라도 들려주는 것이 원칙.

### 강사님 질문 예상 답변

> "API Key 없는 요청은 어떻게 처리해요?"  
→ `_verify_api_key`에서 401 반환합니다. 단, 개발 환경에서는 API_KEY 환경변수를 비워두면 인증 없이 사용 가능합니다.

> "서버 에러가 나면 앱은 어떻게 돼요?"  
→ `global_exception_handler`가 항상 `sentence` 필드를 포함한 JSON을 반환하므로, Android는 그 문장을 TTS로 읽어줍니다.

---

## 3. SQLite와 PostgreSQL의 SQL 문법 차이

### 핵심 한 줄
> **우리 코드는 if/else로 두 가지 SQL을 나눠 작성했고, 가장 큰 차이는 플레이스홀더 기호(`?` vs `%s`)와 자동증가 컬럼 선언 방식이다.**

### 주요 차이점

| 항목 | SQLite | PostgreSQL |
|---|---|---|
| 플레이스홀더 | `?` | `%s` |
| 자동증가 ID | `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL PRIMARY KEY` |
| 커서 사용 | `conn.execute()` 직접 | `conn.cursor()` 필요 |
| 실수형 | `REAL` | `DOUBLE PRECISION` |
| 연결 방법 | `sqlite3.connect(파일명)` | `psycopg_pool.ConnectionPool(URL)` |

### 우리 코드에서 어떻게 해결했나

```python
# db.py — 실제 코드 패턴
def save_gps(session_id, lat, lng):
    with _conn() as conn:
        if _IS_POSTGRES:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO gps_history (...) VALUES (%s, %s, %s, %s)",
                    (session_id, lat, lng, ts)
                )
        else:
            conn.execute(
                "INSERT INTO gps_history (...) VALUES (?, ?, ?, ?)",
                (session_id, lat, lng, ts)
            )
```

`DATABASE_URL` 환경변수가 있으면 PostgreSQL(Supabase), 없으면 SQLite로 자동 전환.  
로컬 개발 → SQLite, GCP Cloud Run → PostgreSQL.

### 강사님 질문 예상 답변

> "왜 두 가지 DB를 지원해요?"  
→ 로컬에서는 파일 하나(SQLite)로 빠르게 테스트하고, 배포 환경(Cloud Run)에서는 여러 인스턴스가 공유할 수 있는 외부 DB(Supabase PostgreSQL)를 씁니다.

> "DB를 바꾸면 코드 많이 고쳐야 해요?"  
→ `DATABASE_URL` 환경변수 하나만 설정/해제하면 됩니다. `_conn()` 컨텍스트 매니저가 내부에서 자동으로 분기합니다.

---

## 4. 안전 서비스의 개인정보/GPS 보관 최소화 사례

### 핵심 한 줄
> **개인을 식별할 수 없는 익명 ID만 쓰고, 오래된 데이터는 자동 삭제하며, 꼭 필요한 것만 저장한다.**

### 개인정보 최소화 원칙 (우리 코드 적용 내용)

| 원칙 | 우리 구현 |
|---|---|
| 최소 수집 | GPS 좌표만 저장, 이름/전화번호 없음 |
| 익명화 | session_id = WiFi SSID (개인 식별 불가) |
| 보관 제한 | GPS 이력 세션당 최대 200개 자동 삭제 |
| 공간 스냅샷 제한 | 공간당 최근 20개만 유지 |
| 대시보드 노출 | 좌표만 표시, 사용자 신원 정보 없음 |

```python
# db.py — 자동 정리 코드
_SNAPSHOT_KEEP = 20  # 공간별 최대 20개
# 20개 초과 시 오래된 것부터 삭제
cur.execute(
    "DELETE FROM snapshots WHERE space_id = %s AND id NOT IN "
    "(SELECT id FROM snapshots WHERE space_id = %s ORDER BY id DESC LIMIT %s)",
    (space_id, space_id, _SNAPSHOT_KEEP)
)
```

### 실제 서비스 사례 참고

- **애플 낙상 감지**: 위치 공유는 SOS 발생 시에만, 평상시엔 저장 안 함
- **구글 맵 타임라인**: 기기 내 저장 (서버 전송 X), 사용자가 직접 삭제 가능
- **네이버 지도 길안내**: 경로 계산 후 좌표 서버에 보관하지 않음

### 강사님 질문 예상 답변

> "GPS 데이터 개인정보 문제 없어요?"  
→ WiFi SSID를 ID로 쓰기 때문에 특정 개인과 연결되지 않습니다. 좌표도 세션당 최대 200개만 유지하고 자동 삭제합니다. 이름, 전화번호 같은 개인식별정보는 저장하지 않습니다.

> "데이터를 언제까지 보관해요?"  
→ 서버 재시작 시 SQLite는 초기화됩니다. PostgreSQL(Supabase)는 최대 보관 개수가 코드로 제한됩니다. 발표 후에는 DB를 비울 계획입니다.

---

## 5. 대시보드 UX에서 실시간 상태를 간결하게 보여주는 사례

### 핵심 한 줄
> **폴링(2초 간격 API 호출)으로 상태를 갱신하고, 위험도 3단계 색상과 카드 UI로 한눈에 파악할 수 있게 한다.**

### 우리 대시보드 구현 방식

```javascript
// dashboard.html — 폴링 구조
const POLL_MS = 2000;  // 2초마다 서버에 묻기

async function poll() {
    const res  = await fetch(`/status/${sessionId}`);
    const data = await res.json();
    renderObjects(data.objects);  // 탐지 물체 카드 갱신
    renderGps(data.gps, data.track);  // 지도 마커 이동
}

setInterval(poll, POLL_MS);  // 2초마다 반복
```

**WebSocket 대신 폴링을 쓴 이유:**  
WebSocket은 지속 연결이 필요해서 Cloud Run 인스턴스가 꺼지면 연결이 끊김. 폴링은 단순하고 인스턴스 재시작에도 자동으로 복구됨.

### 위험도 3단계 색상 체계

| 단계 | 색상 | 기준 |
|---|---|---|
| 위험 (critical) | 빨강 | 차량·계단·칼 또는 2.5m 이내 |
| 주의 (beep) | 노랑 | 2.5m~7m |
| 안전 (silent) | 초록 | 7m 이상 |

서버의 `get_alert_mode()`와 대시보드 `getRisk()`가 같은 기준을 씀 → 앱과 대시보드가 동일한 판단.

### 실제 서비스 사례 참고

- **Grafana 모니터링**: 패널별 색상 임계값, 빠른 폴링으로 실시간 그래프
- **항공 관제 시스템**: 고위험 항공기만 강조(빨강), 나머지는 초록
- **병원 ICU 모니터**: 알람 피로 줄이기 위해 tier별 색상 + 소리 분리

### 강사님 질문 예상 답변

> "실시간이라고 했는데 WebSocket 아닌가요?"  
→ 폴링(2초 주기)입니다. WebSocket은 Cloud Run 환경에서 연결 유지가 불안정해서 단순한 폴링을 선택했습니다. 시연에서는 2초 갱신이 충분합니다.

> "대시보드 색상은 어떤 기준이에요?"  
→ 서버의 `get_alert_mode()` 함수와 동일한 기준입니다. 2.5m 이내면 빨강(critical), 7m 이내면 노랑(beep), 그 이상이면 초록(silent)입니다. 차량은 8m 이내면 무조건 빨강입니다.
