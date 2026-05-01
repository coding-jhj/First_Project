# Supabase Q&A

현재 서버 기준은 GCP Cloud Run + `src.api.main:app`입니다. Supabase는 선택 DB입니다.

## Q1. Supabase를 직접 실행하나요?

아닙니다.

> Supabase는 로컬 Docker로 띄우는 것이 아니라, 클라우드 PostgreSQL에 `DATABASE_URL`로 접속하는 방식입니다.

## Q2. 없어도 서버가 도나요?

돕니다.

| `DATABASE_URL` | DB 모드 |
|---|---|
| 없음 | SQLite |
| 있음 | PostgreSQL/Supabase |

SQLite 모드는 로컬과 GCP 기본 동작 확인에 충분합니다. Supabase는 외부 DB가 필요할 때만 켭니다.

## Q3. 외부 접속은 어떻게 확인하나요?

GCP Cloud Run 환경변수에 `DATABASE_URL`을 넣고 `/health`를 확인합니다.

```json
{
  "db_mode": "postgresql"
}
```

`db_mode`가 `sqlite`로 나오면 Supabase가 연결되지 않은 상태지만, 서버 자체가 실패한 것은 아닙니다.

## Q4. 발표 때 어떻게 말하나요?

> DB는 기본 SQLite로 동작하고, GCP 환경변수에 Supabase 연결 문자열을 넣으면 PostgreSQL로 전환됩니다. 현재 핵심 서버는 `src.api.main:app` 하나이고, legacy의 `server_db`는 학습 기록입니다.

## 핵심 키워드

| 용어 | 뜻 |
|---|---|
| Hosted | Supabase가 운영하는 클라우드 DB |
| Connection string | `postgresql://...` 형태 접속 주소 |
| Pooler | 네트워크 제한을 우회하기 쉬운 연결 주소 |
| SQLite fallback | 외부 DB 없이도 서버가 도는 기본 모드 |
