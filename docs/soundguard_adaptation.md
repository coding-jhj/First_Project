# SoundGuard 대시보드 → VoiceGuide 적용 방법

> 코드는 건드리지 않고, **어디를 어떻게 바꾸면 되는지** 설명합니다.

---

## 1. 두 대시보드 비교

### SoundGuard가 보여주는 것

```
[헤더: SoundGuard | 가산역 | admin]
┌──────────────┬──────────────────────────┬─────────────────┐
│ 왼쪽         │ 지도 (대형)              │ 오른쪽          │
│              │                          │                 │
│ 🚨 무단침입  │   (Leaflet 지도)         │ 감지 판단 요약  │
│  00:16       │                          │  BEAT: 배경음   │
│              │                          │  STT: 아 배고프다│
│ 구역: 가산역 ├──────────────────────────│  대응 메시지:   │
│ 마이크: #1   │ 실시간 동향 분석         │  경고 조건 확인 │
│              │  가장 강한 감지음        │                 │
│ 👤 인원 감지 │  배경음 ████████ 97%    │ [CCTV 패널]    │
│  구역 내 비허│  사람목소리 ░ 2%         │                 │
│  가 인원 존재│  발소리     0%           │                 │
│              │  문소리     0%           │                 │
│ 이벤트 로그  │                          │                 │
│  음성인식결과│                          │                 │
│  무단침입    │                          │                 │
└──────────────┴──────────────────────────┴─────────────────┘
```

### VoiceGuide가 지금 보여주는 것

```
[헤더: VoiceGuide | 세션ID 입력 | 연결상태]
┌──────────────────────┬────────────────────────────────────┐
│ 왼쪽 (340px)         │ 지도 (나머지 전체)                 │
│                      │                                    │
│ [위험 0 주의 0 안전 0]│   (Leaflet 지도)                  │
│                      │                                    │
│ 탐지된 물체:         │   GPS 좌표 카드 (우상단)           │
│  🔴 사람 | 12시 | 위험│                                    │
│  🟡 의자 | 3시  | 주의│   범례 (좌하단)                   │
│  ...                 │                                    │
├──────────────────────┤                                    │
│ 최근 24시간 내역     │                                    │
│  위험 2 주의 5 안전 3 │                                    │
│  13:24 사람          │                                    │
│  13:21 자전거        │                                    │
└──────────────────────┴────────────────────────────────────┘
```

---

## 2. 뭘 적용할 수 있고, 뭘 못 하나

| SoundGuard 요소 | VoiceGuide 적용 가능 여부 | VoiceGuide에서의 대응 요소 |
|----------------|--------------------------|--------------------------|
| 🚨 알림 상태 카드 (무단침입 + 타이머) | ✅ 적용 가능 | critical/beep/silent → "위험!" 카드 + NLG 문장 |
| 실시간 바 차트 (배경음 97%) | ✅ 적용 가능 | 탐지된 물체별 risk_score 바 차트 |
| 가장 강한 감지음 이름 강조 | ✅ 적용 가능 | 가장 위험한 물체 이름 빨간 강조 |
| STT 결과 표시 | ✅ 적용 가능 | 질문/찾기 모드 시 query_text 표시 |
| 대응 메시지 패널 | ✅ 적용 가능 | NLG sentence (음성 안내 문장) |
| 이벤트 로그 | ✅ 이미 있음 | 24시간 탐지 내역 (이미 구현됨) |
| 지도 | ✅ 이미 있음 | Leaflet 지도 (이미 구현됨) |
| CCTV 패널 | ❌ 불가 | 영상 스트림 없음 → 이동속도/거리 정보로 대체 |
| 구역 설정 (가산역) | ❌ 해당 없음 | 세션 ID가 비슷한 역할 |

---

## 3. 목표 레이아웃 (변경 후)

```
[헤더: VoiceGuide | 세션ID | 연결상태]
┌──────────┬────────────────────────────┬───────────────┐
│ 왼쪽     │ 지도                       │ 오른쪽        │
│ 280px    │ (상단 60%)                 │ 280px         │
│          │                            │               │
│ 🚨 위험! │                            │ 현재 안내     │
│  사람이  │                            │ "앞에 사람이  │
│  다가옴  │                            │  있습니다"    │
│          │                            │               │
│ 세션 정보│                            │ 모드: 장애물  │
│ 기기명   │                            │ STT: 앞에 뭐야│
│          ├────────────────────────────│               │
│ 탐지 물체│ 실시간 위험도 분석         │ 이동 정보     │
│  (위험   │ (하단 40%)                 │ 거리: 2.1m   │
│  물체만) │  사람  ████████ 0.82       │ 방향: 12시    │
│          │  의자  ████░    0.45       │               │
│ 이벤트   │  기둥  ██░░     0.22       │               │
│ 로그     │                            │               │
└──────────┴────────────────────────────┴───────────────┘
```

---

## 4. 레이아웃 구조 변경 방법

### 파일: `templates/dashboard.html`

---

### 4-A. 그리드를 3열로 변경

**현재 (100번 줄 근처):**
```css
main {
  display: grid;
  grid-template-columns: 340px 1fr;   /* 2열 */
  overflow: hidden;
}
```

**변경 후:**
```css
main {
  display: grid;
  grid-template-columns: 280px 1fr 280px;   /* 3열 */
  overflow: hidden;
}
```

---

### 4-B. 지도 영역을 상하로 분리

**현재 HTML (563번 줄 근처):**
```html
<!-- 오른쪽: 지도 -->
<div class="map-container">
  <div id="map"></div>
  ...
</div>
```

**변경 후:**
```html
<!-- 중앙: 지도 + 분석 패널 -->
<div class="center-column">
  
  <!-- 위: 지도 (60%) -->
  <div class="map-container">
    <div id="map"></div>
    ... (GPS 카드, 범례 등 그대로)
  </div>
  
  <!-- 아래: 실시간 위험도 바 차트 (40%) -->
  <div class="analysis-panel">
    <div class="section-title">실시간 위험도 분석</div>
    <div id="riskBarChart">
      <!-- JS가 여기에 바 차트 그려줌 -->
    </div>
  </div>

</div>
```

**CSS 추가:**
```css
.center-column {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.map-container {
  flex: 6;   /* 60% */
}

.analysis-panel {
  flex: 4;   /* 40% */
  background: var(--surface);
  border-top: 1px solid var(--border);
  padding: 16px 20px;
  overflow-y: auto;
}
```

---

### 4-C. 왼쪽 패널 — 알림 카드 추가

왼쪽 패널 맨 위에 SoundGuard의 "무단침입 카드"처럼 현재 상태를 강조하는 카드를 추가합니다.

**HTML — panel-top 안, stats-grid 위에 삽입:**
```html
<!-- 현재 경보 상태 카드 (SoundGuard의 무단침입 카드 역할) -->
<div class="panel-section" id="alertCardSection">
  <div id="alertCard" class="alert-card alert-safe">
    <div class="alert-icon">✅</div>
    <div class="alert-body">
      <div class="alert-title" id="alertTitle">안전</div>
      <div class="alert-desc" id="alertDesc">탐지된 위험물 없음</div>
    </div>
  </div>
</div>
```

**CSS 추가:**
```css
.alert-card {
  border-radius: var(--radius);
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  border: 1px solid;
}

.alert-card.alert-critical {
  background: rgba(255,77,109,0.12);
  border-color: var(--danger);
  animation: blink-border 1s infinite;
}

.alert-card.alert-beep {
  background: rgba(244,162,97,0.12);
  border-color: var(--warn);
}

.alert-card.alert-safe {
  background: rgba(82,183,136,0.1);
  border-color: var(--safe);
}

.alert-icon { font-size: 28px; }
.alert-title { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
.alert-desc { font-size: 12px; color: var(--muted); }

@keyframes blink-border {
  0%, 100% { border-color: var(--danger); }
  50%       { border-color: transparent; }
}
```

---

### 4-D. 오른쪽 패널 추가 (새 HTML 블록)

`</main>` 직전에 오른쪽 패널 `<div>` 를 추가합니다.

```html
<!-- 오른쪽: 안내 요약 패널 -->
<div class="panel right-panel">

  <!-- 현재 음성 안내 문장 -->
  <div class="panel-section">
    <div class="section-title">현재 안내</div>
    <div id="nlgSentence" class="nlg-box">
      대기 중...
    </div>
  </div>

  <!-- 모드 + STT -->
  <div class="panel-section">
    <div class="section-title">감지 판단</div>
    <div class="info-row">
      <span class="info-label">모드</span>
      <span class="info-value" id="currentMode">—</span>
    </div>
    <div class="info-row">
      <span class="info-label">음성 명령</span>
      <span class="info-value" id="sttText">—</span>
    </div>
    <div class="info-row">
      <span class="info-label">경보 수준</span>
      <span class="info-value" id="alertMode">—</span>
    </div>
  </div>

  <!-- 가장 위험한 물체 정보 -->
  <div class="panel-section">
    <div class="section-title">주요 위험 물체</div>
    <div id="topObjectPanel">
      <div style="color:var(--muted); font-size:12px;">없음</div>
    </div>
  </div>

</div>
```

**CSS 추가:**
```css
.right-panel {
  border-right: none;
  border-left: 1px solid var(--border);
}

.nlg-box {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  min-height: 60px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.info-label { color: var(--muted); }
.info-value { font-weight: 600; }
```

---

## 5. JS 연결 — 어떤 데이터를 어디에 넣나

현재 대시보드는 `/events/{session_id}` SSE 스트림에서 실시간 데이터를 받습니다.  
받은 데이터에는 `objects`, `latest_event` 등이 포함돼 있습니다.

**기존 JS에서 데이터를 처리하는 함수를 찾아 아래 내용을 추가하면 됩니다.**

대시보드 HTML 안 `<script>` 태그에서 `renderStatus(data)` 또는 비슷한 함수를 찾으세요.  
그 함수 끝에 아래 코드를 추가합니다:

```javascript
// ─── 알림 카드 업데이트 ───────────────────────────────
function updateAlertCard(objects) {
  const card = document.getElementById('alertCard');
  const title = document.getElementById('alertTitle');
  const desc = document.getElementById('alertDesc');
  
  if (!objects || objects.length === 0) {
    card.className = 'alert-card alert-safe';
    title.textContent = '안전';
    desc.textContent = '탐지된 위험물 없음';
    return;
  }
  
  const top = objects[0];  // 위험도 순 정렬된 첫 번째 물체
  const risk = top.risk_score || 0;
  
  if (risk >= 0.7) {
    card.className = 'alert-card alert-critical';
    title.textContent = '위험!';
    desc.textContent = `${top.class_ko}이(가) ${top.direction} 방향`;
  } else if (risk >= 0.4) {
    card.className = 'alert-card alert-beep';
    title.textContent = '주의';
    desc.textContent = `${top.class_ko} 감지됨`;
  } else {
    card.className = 'alert-card alert-safe';
    title.textContent = '안전';
    desc.textContent = '위험 물체 없음';
  }
}

// ─── 위험도 바 차트 업데이트 ─────────────────────────
function updateRiskChart(objects) {
  const container = document.getElementById('riskBarChart');
  if (!container) return;
  
  if (!objects || objects.length === 0) {
    container.innerHTML = '<div style="color:var(--muted);font-size:12px;">탐지된 물체 없음</div>';
    return;
  }
  
  container.innerHTML = objects.slice(0, 5).map(obj => {
    const pct = Math.round((obj.risk_score || 0) * 100);
    const color = pct >= 70 ? 'var(--danger)' : pct >= 40 ? 'var(--warn)' : 'var(--safe)';
    return `
      <div style="margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;">
          <span>${obj.class_ko} (${obj.direction})</span>
          <span style="color:${color};font-weight:700;">${pct}%</span>
        </div>
        <div style="background:var(--surface2);border-radius:4px;height:8px;">
          <div style="background:${color};width:${pct}%;height:100%;border-radius:4px;transition:width 0.4s;"></div>
        </div>
      </div>
    `;
  }).join('');
}

// ─── 오른쪽 패널 업데이트 ────────────────────────────
function updateRightPanel(data) {
  // NLG 문장
  const sentence = data.latest_event?.objects?.[0] ? '' : '';  // sentence는 SSE 데이터에 없으므로
  // → sentence 데이터가 없다면 latest_event의 objects로 유추하거나 생략
  
  // 모드
  const modeEl = document.getElementById('currentMode');
  if (modeEl) modeEl.textContent = data.latest_event?.mode || '장애물';
  
  // 주요 위험 물체
  const topPanel = document.getElementById('topObjectPanel');
  const obj = data.objects?.[0];
  if (topPanel && obj) {
    const pct = Math.round((obj.risk_score || 0) * 100);
    topPanel.innerHTML = `
      <div style="font-size:22px;font-weight:700;color:var(--danger);margin-bottom:4px;">
        ${obj.class_ko}
      </div>
      <div style="font-size:12px;color:var(--muted);">
        ${obj.direction} 방향 · ${obj.distance_m || '?'}m · 위험도 ${pct}%
      </div>
    `;
  }
}
```

**기존 `renderStatus(data)` 함수 끝에 호출 추가:**
```javascript
function renderStatus(data) {
  // ... 기존 코드 ...
  
  // 새로 추가하는 부분
  updateAlertCard(data.objects);
  updateRiskChart(data.objects);
  updateRightPanel(data);
}
```

---

## 6. 작업 순서 (쉬운 것부터)

| 순서 | 작업 | 난이도 | 효과 |
|------|------|--------|------|
| 1 | 알림 카드 추가 (CSS + HTML) | ★☆☆ | 현재 상태가 한눈에 보임 |
| 2 | `updateAlertCard()` JS 연결 | ★☆☆ | 카드가 실시간으로 빨간색/초록색 변환 |
| 3 | 위험도 바 차트 추가 (HTML) | ★☆☆ | SoundGuard와 가장 비슷한 부분 |
| 4 | `updateRiskChart()` JS 연결 | ★★☆ | 바 차트 실시간 업데이트 |
| 5 | 그리드 3열로 변경 | ★★☆ | 오른쪽 패널 공간 확보 |
| 6 | 오른쪽 패널 HTML 추가 | ★☆☆ | NLG 문장, 모드, 물체 정보 |
| 7 | `updateRightPanel()` JS 연결 | ★★☆ | 오른쪽 패널 실시간 업데이트 |

> 1~4번만 해도 SoundGuard의 핵심 느낌(바 차트 + 상태 카드)은 구현됩니다.  
> 5~7번은 여유가 있을 때 하면 됩니다.

---

## 7. 못 쓰는 부분 (이유 포함)

### CCTV 패널
- SoundGuard는 실제 카메라 영상 스트림을 보여줌
- VoiceGuide는 서버에 영상이 없음 (온디바이스에서만 처리)
- → 대신 "현재 안내 문장" 또는 "이동 경로 통계" 패널로 채우면 됨

### 구역 기반 센서 표시
- SoundGuard는 물리적 구역(가산역, 마이크 #1)에 고정된 센서가 있음
- VoiceGuide는 이동하는 개인 기기가 기준
- → 세션 ID = "기기 이름" 역할로 대체

---

## 8. 완성 시 화면 설명 (발표용)

> "왼쪽에서는 현재 위험 상태와 탐지된 물체를,  
> 가운데 지도에서는 이동 경로를,  
> 아래 바 차트에서는 각 물체의 위험도를 실시간으로 확인할 수 있습니다.  
> 오른쪽에서는 앱이 사용자에게 실제로 전달하는 음성 안내 문장을 볼 수 있습니다."
