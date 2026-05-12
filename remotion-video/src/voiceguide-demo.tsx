import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  Video,
  interpolate,
  staticFile,
  useCurrentFrame,
} from 'remotion';

type Props = {presenter: string};

const FPS = 30;
const TOTAL = 530;
const f = (s: number) => Math.round(s * FPS);
const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

const ease = (frame: number, from: number, to: number, len = 36) =>
  interpolate(frame, [0, len], [from, to], {easing: Easing.out(Easing.cubic), ...clamp});

const fadeIn = (frame: number, delay = 0, dur = 24) =>
  interpolate(frame, [delay, delay + dur], [0, 1], clamp);

// ── Progress bar ────────────────────────────────────────────────────────────
const Progress: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div style={s.progressTrack}>
      <div style={{...s.progressFill, width: `${interpolate(frame, [0, f(TOTAL)], [0, 100], clamp)}%`}} />
    </div>
  );
};

// ── Section title ───────────────────────────────────────────────────────────
const Title: React.FC<{eyebrow: string; headline: string; sub?: string; light?: boolean}> = ({
  eyebrow, headline, sub, light = false,
}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{opacity: fadeIn(frame, 0, 24), transform: `translateY(${ease(frame, 28, 0)}px)`}}>
      <div style={light ? s.eyebrowLight : s.eyebrow}>{eyebrow}</div>
      <h1 style={light ? s.h1Light : s.h1}>{headline}</h1>
      {sub && <p style={light ? s.subLight : s.sub}>{sub}</p>}
    </div>
  );
};

// ── Lower-third overlay ─────────────────────────────────────────────────────
const LowerThird: React.FC<{kicker: string; title: string; caption: string}> = ({kicker, title, caption}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{...s.lt, opacity: fadeIn(frame, 0, 20), transform: `translateY(${ease(frame, 22, 0)}px)`}}>
      <div style={s.ltKicker}>{kicker}</div>
      <div style={s.ltTitle}>{title}</div>
      <div style={s.ltCaption}>{caption}</div>
    </div>
  );
};

// ── Scene 1: Opening (0–30s) ────────────────────────────────────────────────
const Opening: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={s.opening}>
      <div style={s.openingGrid}>
        <div style={{opacity: fadeIn(frame, 0, 28), transform: `translateX(${ease(frame, -40, 0)}px)`}}>
          <div style={s.brand}>VoiceGuide</div>
          <div style={s.teamBadge}>3팀</div>
          <h1 style={s.heroTitle}>스마트폰 카메라로<br />지금 앞의 위험을<br />감지합니다</h1>
          <p style={s.heroSub}>실시간 객체 탐지 기반 시각장애인 보행 보조 앱</p>
        </div>
        <div style={{...s.phoneWrap, opacity: fadeIn(frame, 10, 28)}}>
          <Img src={staticFile('assets/device-shots/debug-fps.png')} style={s.phoneImg} />
          <div style={s.phoneGlass} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 2: Problem (30–80s) ───────────────────────────────────────────────
const Problem: React.FC = () => {
  const frame = useCurrentFrame();
  const stats = [
    {n: '2,627,761', u: '명', l: '국내 등록 장애인'},
    {n: '245,361', u: '명', l: '시각장애인'},
    {n: '44,083', u: '명', l: '심한 시각장애인'},
  ];
  const issues = [
    ['흰 지팡이', '근거리 촉각 중심 — 전방 위험 감지 불가'],
    ['GPS 안내 앱', '경로 중심 — 지금 앞의 장애물 인식 안 함'],
    ['보행 인프라', '설치 사각지대 존재'],
    ['서버 추론형 앱', '네트워크 지연, 오프라인 취약'],
  ];
  return (
    <AbsoluteFill style={s.white}>
      <div style={s.twoCol}>
        <div>
          <Title eyebrow="01. 문제 정의" headline="길을 아는 것만으로는 부족합니다." sub="중요한 것은 지금 앞의 위험입니다." />
          <div style={s.statRow}>
            {stats.map(({n, u, l}, i) => (
              <div key={l} style={{...s.statCard, opacity: fadeIn(frame, i * 10 + 24, 20), transform: `translateY(${ease(frame - (i * 10 + 24), 20, 0)}px)`}}>
                <div style={s.statNum}>{n}<span style={s.statUnit}>{u}</span></div>
                <div style={s.statLabel}>{l}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={s.issueStack}>
          {issues.map(([t, b], i) => (
            <div key={t} style={{...s.issueCard, opacity: fadeIn(frame, i * 9 + 20, 18), transform: `translateX(${ease(frame - (i * 9 + 20), 36, 0)}px)`}}>
              <b style={s.issueTitle}>{t}</b>
              <span style={s.issueBody}>{b}</span>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 3: Service Concept (80–120s) ─────────────────────────────────────
const ServiceConcept: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={s.dark}>
      <div style={s.conceptWrap}>
        <Title eyebrow="02. 서비스 개념" headline="길 안내를 대체하지 않습니다." sub="지금 앞의 위험을 한 번 더 알려주는 보조 안전 레이어입니다." light />
        <div style={s.compareRow}>
          <div style={{...s.compareCard, ...s.compareL, opacity: fadeIn(frame, 20, 22), transform: `translateX(${ease(frame - 20, -30, 0)}px)`}}>
            <div style={s.cTag}>기존 GPS 안내 앱</div>
            <div style={s.cIcon}>🗺️</div>
            <div style={s.cTitle}>경로 안내</div>
            <div style={s.cDesc}>목적지까지 어떻게 가는지 알려줍니다</div>
          </div>
          <div style={{...s.plusWrap, opacity: fadeIn(frame, 30, 20)}}>
            <span style={s.plus}>+</span>
          </div>
          <div style={{...s.compareCard, ...s.compareR, opacity: fadeIn(frame, 24, 22), transform: `translateX(${ease(frame - 24, 30, 0)}px)`}}>
            <div style={s.cTagGreen}>VoiceGuide</div>
            <div style={s.cIcon}>📱</div>
            <div style={s.cTitle}>현재 전방 위험 보조</div>
            <div style={s.cDesc}>지금 앞의 장애물을 즉시 음성·진동으로 알려줍니다</div>
          </div>
        </div>
        <div style={{...s.safetyBanner, opacity: fadeIn(frame, 55, 24)}}>
          보조 안전 레이어 — 보행 인프라를 대체하는 것이 아니라, 이동 중 한 번 더 알려주는 추가 안전망입니다.
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 4: Architecture (120–170s) ───────────────────────────────────────
const Architecture: React.FC = () => {
  const frame = useCurrentFrame();
  const android = ['CameraX', 'TFLite YOLO', 'Vote + Dedup', 'IoU Tracking', 'EMA Smoothing', 'TTS · 진동'];
  const server = ['POST /detect', 'POST /gps', 'FastAPI', 'DB (SQLite / PG)', 'SSE Events', 'Dashboard'];
  return (
    <AbsoluteFill style={s.dark}>
      <div style={s.archWrap}>
        <Title eyebrow="03. 전체 구조" headline="판단은 Android에서 즉시, 기록은 서버에서." light />
        <div style={{...s.archNote, opacity: fadeIn(frame, 18, 20)}}>
          서버는 영상을 받아 YOLO를 돌리지 않습니다 — Android가 탐지한 결과 JSON만 서버로 전송됩니다.
        </div>
        <div style={s.archPanels}>
          {([
            {label: '📱 Android', nodes: android, accent: false},
            {label: '🖥️ Server', nodes: server, accent: true},
          ] as const).map(({label, nodes, accent}, pi) => (
            <div key={label} style={{...s.archPanel, ...(accent ? s.archPanelAccent : {})}}>
              <div style={s.archPanelLabel}>{label}</div>
              {nodes.map((n, i) => (
                <div key={n} style={{...s.archNode, opacity: fadeIn(frame, pi * 8 + i * 5 + 22, 16), transform: `translateX(${ease(frame - (pi * 8 + i * 5 + 22), 18, 0)}px)`}}>
                  <span style={s.archNum}>{String(i + 1).padStart(2, '0')}</span>
                  <span style={s.archNodeText}>{n}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 5: AppDemo – Object Detection (170–260s) ─────────────────────────
const OBJECTS = [
  {img: 'assets/test-images/chair.jpg',    label: 'chair',    conf: '0.91', dist: '약 1.5m', tts: '정면 약 1.5m에 의자가 있어요.',   vib: 'SHORT'},
  {img: 'assets/test-images/person.jpg',   label: 'person',   conf: '0.87', dist: '약 2m',   tts: '정면 약 2m에 사람이 있어요.',      vib: 'DOUBLE'},
  {img: 'assets/test-images/door.jpg',     label: 'door',     conf: '0.93', dist: '약 1m',   tts: '정면 약 1m에 문이 있어요.',        vib: 'SHORT'},
  {img: 'assets/test-images/stairs.jpg',   label: 'stairs',   conf: '0.88', dist: '약 1m',   tts: '바로 앞에 계단이 있어요.',         vib: 'URGENT'},
  {img: 'assets/test-images/backpack.jpg', label: 'backpack', conf: '0.79', dist: '약 2.5m', tts: '정면 약 2.5m에 가방이 있어요.',    vib: 'NONE'},
];
const CYCLE = 18;

const AppDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const idx = Math.min(Math.floor(frame / f(CYCLE)), OBJECTS.length - 1);
  const obj = OBJECTS[idx];
  const lf = frame - idx * f(CYCLE);
  const vibColor = obj.vib === 'URGENT' ? '#f87171' : obj.vib === 'NONE' ? '#64748b' : '#5eead4';

  return (
    <AbsoluteFill style={s.dark}>
      <div style={s.demoLayout}>
        <div style={s.demoPhoneWrap}>
          <div style={s.demoPhoneFrame}>
            <Img src={staticFile(obj.img)} style={s.demoPhoneImg} />
            <div style={{...s.bbox, opacity: fadeIn(lf, 4, 12)}}>
              <div style={s.bboxLabel}>{obj.label} {obj.conf}</div>
            </div>
            <div style={{...s.ttsCaption, opacity: fadeIn(lf, 14, 14)}}>
              🔊 {obj.tts}
            </div>
          </div>
        </div>
        <div style={s.demoRight}>
          <Title eyebrow="04. 객체 탐지 시연" headline="CameraX 프레임을 TFLite YOLO로 분석합니다." light />
          <div style={s.demoCards}>
            {[
              ['탐지 객체', obj.label, '#5eead4'],
              ['신뢰도', obj.conf, '#5eead4'],
              ['추정 거리', obj.dist, '#5eead4'],
              ['진동 패턴', obj.vib, vibColor],
            ].map(([lbl, val, color], i) => (
              <div key={lbl} style={{...s.demoCard, opacity: fadeIn(lf, i * 6 + 10, 16)}}>
                <div style={s.demoCardLabel}>{lbl}</div>
                <div style={{...s.demoCardVal, color}}>{val}</div>
              </div>
            ))}
          </div>
          <div style={{...s.ttsBox, opacity: fadeIn(lf, 26, 18)}}>
            <div style={s.ttsBoxLabel}>🔊 TTS 안내</div>
            <div style={s.ttsBoxText}>"{obj.tts}"</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 6: Voice + Vibration Feedback (260–310s) ─────────────────────────
const Feedback: React.FC = () => {
  const frame = useCurrentFrame();
  const levels = [
    {vib: 'NONE',   score: '< 0.35', color: '#64748b', desc: '진동 없음'},
    {vib: 'SHORT',  score: '≥ 0.35', color: '#22c55e', desc: '짧은 1회'},
    {vib: 'DOUBLE', score: '≥ 0.55', color: '#f59e0b', desc: '짧은 2회'},
    {vib: 'URGENT', score: '≥ 0.75', color: '#ef4444', desc: '긴급 반복'},
  ];
  return (
    <AbsoluteFill style={s.dark}>
      <div style={s.feedbackWrap}>
        <Title eyebrow="05. 음성·진동 안내" headline="위험도에 따라 안내 방식이 달라집니다." sub="화면을 보지 않아도 즉시 이해되는 짧은 문장과 진동으로 안내합니다." light />
        <div style={s.vibGrid}>
          {levels.map(({vib, score, color, desc}, i) => {
            const pulse = interpolate((frame + i * 12) % 48, [0, 24, 48], [0.97, 1.03, 0.97], clamp);
            return (
              <div key={vib} style={{...s.vibCard, borderColor: color, opacity: fadeIn(frame, i * 10 + 24, 20), transform: `scale(${vib !== 'NONE' ? pulse : 1})`}}>
                <div style={{...s.vibBadge, backgroundColor: color}}>{vib}</div>
                <div style={s.vibScore}>위험도 {score}</div>
                <div style={s.vibDesc}>{desc}</div>
              </div>
            );
          })}
        </div>
        <div style={{...s.speechCard, opacity: fadeIn(frame, 58, 24)}}>
          <div style={s.speechLabel}>🔊 안내 예시 (URGENT)</div>
          <div style={s.speechText}>"바로 앞에 계단이 있어요."</div>
          <div style={s.speechNote}>위험도 0.82 → 긴급 진동 + 쿨다운 없이 즉시 발화</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 7: Server Upload (310–360s) ──────────────────────────────────────
const ServerUpload: React.FC = () => {
  const frame = useCurrentFrame();
  const apis = [
    {method: 'POST', path: '/detect',        desc: '탐지 결과 JSON 전송',  detail: '{ class, bbox, risk, session_id }'},
    {method: 'POST', path: '/gps',           desc: 'GPS 위치 기록',        detail: '{ lat, lng, session_id, timestamp }'},
    {method: 'GET',  path: '/status/{id}',   desc: '현재 객체·GPS 조회',   detail: '→ 실시간 단말 상태'},
    {method: 'GET',  path: '/events/{id}',   desc: 'SSE 실시간 스트림',    detail: '→ 대시보드 즉시 반영'},
  ];
  const boxes = [
    {label: '📱 Android', sub: '탐지 완료 → 비동기 전송', style: s.flowBoxA},
    {label: '🖥️ FastAPI', sub: 'GCP Cloud Run', style: s.flowBoxS},
    {label: '🗄️ DB + SSE', sub: 'SQLite / PostgreSQL', style: s.flowBoxD},
  ];
  return (
    <AbsoluteFill style={s.white}>
      <div style={s.uploadWrap}>
        <Title eyebrow="06. 서버 업로드" headline="탐지 결과와 위치를 서버에 기록합니다." sub="Android는 영상을 보내지 않습니다. JSON 결과만 비동기로 전송합니다." />
        <div style={s.flowRow}>
          {boxes.map(({label, sub, style: boxStyle}, i) => (
            <React.Fragment key={label}>
              {i > 0 && <div style={{...s.flowArrow, opacity: fadeIn(frame, i * 7 + 22, 18)}}><span style={s.arrowText}>→</span></div>}
              <div style={{...boxStyle, opacity: fadeIn(frame, i * 7 + 16, 18)}}>
                <div style={s.flowLabel}>{label}</div>
                <div style={s.flowSub}>{sub}</div>
              </div>
            </React.Fragment>
          ))}
        </div>
        <div style={s.apiTable}>
          {apis.map(({method, path, desc, detail}, i) => (
            <div key={path} style={{...s.apiRow, opacity: fadeIn(frame, i * 9 + 34, 18), transform: `translateY(${ease(frame - (i * 9 + 34), 14, 0)}px)`}}>
              <span style={{...s.apiMethod, backgroundColor: method === 'POST' ? '#0f2b4c' : '#0f766e'}}>{method}</span>
              <span style={s.apiPath}>{path}</span>
              <span style={s.apiDesc}>{desc}</span>
              <span style={s.apiDetail}>{detail}</span>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 8: Dashboard Live (360–410s) ─────────────────────────────────────
const Dashboard: React.FC = () => (
  <AbsoluteFill>
    <AbsoluteFill style={{backgroundColor: '#020617', overflow: 'hidden'}}>
      <Video
        src={staticFile('assets/demo.mp4')}
        startFrom={0}
        muted
        style={{position: 'absolute', top: -170, left: -230, width: 2380, height: 1340, objectFit: 'fill'}}
      />
      <AbsoluteFill style={{backgroundColor: 'rgba(3,7,18,0.06)'}} />
    </AbsoluteFill>
    <LowerThird
      kicker="07. 서버 대시보드"
      title="탐지 이벤트가 대시보드로 실시간 전송됩니다"
      caption="Android가 보낸 JSON, 위치, 이벤트 흐름이 같은 session_id로 대시보드에 반영됩니다."
    />
  </AbsoluteFill>
);

// ── Scene 9: Verification (410–450s) ──────────────────────────────────────
const Verification: React.FC = () => {
  const frame = useCurrentFrame();
  const confirmed = [
    ['자동 테스트', '23 passed, 9 deselected'],
    ['서버 요청 평균', '26.37 ms'],
    ['NLG 생성 시간', '0.015 ms'],
  ];
  const pending = ['Android 실기 FPS', 'mAP50 (모델 정확도)', '메모리 사용량', 'TTS-UI latency', '저조도 환경 성능'];
  return (
    <AbsoluteFill style={s.white}>
      <div style={s.verifyWrap}>
        <div>
          <Title eyebrow="08. 검증 결과" headline="확보된 수치와 미측정 항목을 분리했습니다." />
          <div style={{...s.verifySection, color: '#0f766e', opacity: fadeIn(frame, 22, 18)}}>✓ 확보된 수치</div>
          {confirmed.map(([k, v], i) => (
            <div key={k} style={{...s.verifyRow, opacity: fadeIn(frame, i * 8 + 26, 16)}}>
              <span style={s.verifyKey}>{k}</span>
              <b style={s.verifyVal}>{v}</b>
            </div>
          ))}
        </div>
        <div>
          <div style={{...s.verifySection, color: '#b45309', opacity: fadeIn(frame, 38, 18)}}>△ 추가 측정 필요</div>
          {pending.map((item, i) => (
            <div key={item} style={{...s.verifyPending, opacity: fadeIn(frame, i * 7 + 42, 16)}}>
              {item}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 10: Trials (450–500s) ────────────────────────────────────────────
const Trials: React.FC = () => {
  const frame = useCurrentFrame();
  const items = [
    {problem: '객체 알림 과다',   lesson: 'Vote + Dedup + EMA 적용',           direction: '사용자 피로도 기준 조정'},
    {problem: '서버 역할 혼선',   lesson: 'Android 즉시 판단, 서버 기록 분리',  direction: '발표에서 역할 분리 강조'},
    {problem: '거리 추정 한계',   lesson: 'bbox 기반 추정을 보조값으로만 사용', direction: '거리 캘리브레이션·Depth 검토'},
    {problem: '성능 수치 부족',   lesson: '확보 수치와 미측정 항목 분리',        direction: 'FPS·mAP50·메모리 실기 측정'},
  ];
  return (
    <AbsoluteFill style={s.dark}>
      <div style={s.trialsWrap}>
        <Title eyebrow="09. 시행착오" headline="실패 기록이 아니라 개선 근거입니다." light />
        <div style={s.trialsGrid}>
          {items.map(({problem, lesson, direction}, i) => (
            <div key={problem} style={{...s.trialCard, opacity: fadeIn(frame, i * 10 + 24, 20), transform: `translateY(${ease(frame - (i * 10 + 24), 22, 0)}px)`}}>
              <div style={s.trialProblem}>{problem}</div>
              <div style={s.trialLesson}>→ {lesson}</div>
              <div style={s.trialDir}>↗ {direction}</div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 11: Closing (500–530s) ───────────────────────────────────────────
const Closing: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={s.dark}>
      <div style={{...s.closingWrap, opacity: fadeIn(frame, 0, 32)}}>
        <div style={s.brand}>VoiceGuide</div>
        <div style={s.teamBadge}>3팀</div>
        <h1 style={s.heroTitle}>지금 앞의 위험을<br />한 번 더 알려주는<br />보조 안전 레이어</h1>
        <p style={s.heroSub}>탐지, 안내, 기록을 하나의 흐름으로 연결합니다.</p>
      </div>
    </AbsoluteFill>
  );
};

// ── Root ───────────────────────────────────────────────────────────────────
export const VoiceGuideDemo: React.FC<Props> = () => {
  const scenes: Array<[number, number, React.ReactElement]> = [
    [0,   30, <Opening key="o" />],
    [30,  50, <Problem key="p" />],
    [80,  40, <ServiceConcept key="sc" />],
    [120, 50, <Architecture key="ar" />],
    [170, 90, <AppDemo key="ad" />],
    [260, 50, <Feedback key="fb" />],
    [310, 50, <ServerUpload key="su" />],
    [360, 50, <Dashboard key="db" />],
    [410, 40, <Verification key="vr" />],
    [450, 50, <Trials key="tr" />],
    [500, 30, <Closing key="cl" />],
  ];

  return (
    <AbsoluteFill style={s.root}>
      {scenes.map(([start, dur, comp]) => (
        <Sequence key={start} from={f(start)} durationInFrames={f(dur)}>
          <AbsoluteFill>{comp}</AbsoluteFill>
        </Sequence>
      ))}
      <Progress />
    </AbsoluteFill>
  );
};

// ── Styles ─────────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  root: {backgroundColor: '#06111f', fontFamily: '"Noto Sans KR", "Apple SD Gothic Neo", Arial, sans-serif'},
  progressTrack: {position: 'absolute', bottom: 0, left: 0, right: 0, height: 8, backgroundColor: 'rgba(255,255,255,0.15)'},
  progressFill: {height: '100%', backgroundColor: '#5eead4'},
  eyebrow: {color: '#0f766e', fontSize: 26, fontWeight: 900, marginBottom: 16},
  eyebrowLight: {color: '#5eead4', fontSize: 26, fontWeight: 900, marginBottom: 16},
  h1: {color: '#06111f', fontSize: 66, fontWeight: 950, lineHeight: 1.1, margin: 0},
  h1Light: {color: '#ffffff', fontSize: 66, fontWeight: 950, lineHeight: 1.1, margin: 0},
  sub: {color: '#334155', fontSize: 27, fontWeight: 700, lineHeight: 1.45, marginTop: 22, maxWidth: 740},
  subLight: {color: '#cbd5e1', fontSize: 27, fontWeight: 700, lineHeight: 1.45, marginTop: 22, maxWidth: 740},
  lt: {position: 'absolute', bottom: 52, left: 72, width: 1100, padding: '20px 28px', backgroundColor: 'rgba(6,17,31,0.9)', border: '1px solid rgba(94,234,212,0.28)', borderRadius: 8},
  ltKicker: {color: '#5eead4', fontSize: 21, fontWeight: 900, marginBottom: 6},
  ltTitle: {color: '#ffffff', fontSize: 36, fontWeight: 900, lineHeight: 1.15},
  ltCaption: {color: '#cbd5e1', fontSize: 21, fontWeight: 700, marginTop: 8, lineHeight: 1.4},
  white: {backgroundColor: '#f8fafc'},
  dark: {background: 'linear-gradient(135deg, #06111f 0%, #122b39 55%, #0b1728 100%)'},
  opening: {background: 'linear-gradient(135deg, #06111f 0%, #0f2e3a 50%, #f8fafc 50%, #f8fafc 100%)'},
  openingGrid: {display: 'grid', gridTemplateColumns: '1fr 1fr', height: '100%', padding: '100px 90px', gap: 60},
  brand: {color: '#5eead4', fontSize: 30, fontWeight: 950, marginBottom: 10},
  teamBadge: {display: 'inline-block', backgroundColor: 'rgba(94,234,212,0.18)', border: '1px solid rgba(94,234,212,0.4)', borderRadius: 6, color: '#5eead4', fontSize: 21, fontWeight: 800, padding: '5px 14px', marginBottom: 26},
  heroTitle: {color: '#ffffff', fontSize: 74, fontWeight: 950, lineHeight: 1.12, margin: 0},
  heroSub: {color: '#dbeafe', fontSize: 26, fontWeight: 750, lineHeight: 1.5, marginTop: 26},
  phoneWrap: {alignSelf: 'center', justifySelf: 'center', width: 440, height: 780, border: '16px solid #0f172a', borderRadius: 48, overflow: 'hidden', position: 'relative', boxShadow: '0 40px 100px rgba(2,6,23,0.5)'},
  phoneImg: {width: '100%', height: '100%', objectFit: 'cover'},
  phoneGlass: {position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(255,255,255,0.1), transparent)'},
  twoCol: {display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 70, height: '100%', padding: '120px 90px'},
  statRow: {display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginTop: 36},
  statCard: {backgroundColor: '#ffffff', border: '1px solid #dbeafe', borderRadius: 10, padding: '26px 20px', boxShadow: '0 14px 44px rgba(15,23,42,0.08)'},
  statNum: {color: '#0f2b4c', fontSize: 36, fontWeight: 950, lineHeight: 1},
  statUnit: {color: '#0f2b4c', fontSize: 22, fontWeight: 800},
  statLabel: {color: '#64748b', fontSize: 20, fontWeight: 700, marginTop: 8},
  issueStack: {display: 'grid', gap: 18, alignContent: 'center'},
  issueCard: {backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 10, padding: '24px 28px', boxShadow: '0 10px 36px rgba(15,23,42,0.06)', display: 'grid', gap: 8},
  issueTitle: {color: '#0f2b4c', fontSize: 30, fontWeight: 950},
  issueBody: {color: '#475569', fontSize: 22, fontWeight: 700},
  conceptWrap: {padding: '80px 90px', display: 'grid', gap: 44},
  compareRow: {display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 28, alignItems: 'center'},
  compareCard: {borderRadius: 14, padding: '36px 32px', display: 'grid', gap: 16, textAlign: 'center'},
  compareL: {backgroundColor: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.18)'},
  compareR: {backgroundColor: 'rgba(94,234,212,0.1)', border: '1px solid rgba(94,234,212,0.4)'},
  plusWrap: {textAlign: 'center'},
  plus: {color: '#94a3b8', fontSize: 52, fontWeight: 900},
  cTag: {color: '#94a3b8', fontSize: 20, fontWeight: 800},
  cTagGreen: {color: '#5eead4', fontSize: 20, fontWeight: 800},
  cIcon: {fontSize: 50},
  cTitle: {color: '#ffffff', fontSize: 30, fontWeight: 950},
  cDesc: {color: '#cbd5e1', fontSize: 20, fontWeight: 700, lineHeight: 1.4},
  safetyBanner: {backgroundColor: 'rgba(94,234,212,0.1)', border: '1px solid rgba(94,234,212,0.3)', borderRadius: 10, padding: '20px 28px', color: '#e2e8f0', fontSize: 24, fontWeight: 800, lineHeight: 1.5},
  archWrap: {padding: '80px 90px', display: 'grid', gap: 36},
  archNote: {backgroundColor: 'rgba(255,255,255,0.06)', border: '1px solid rgba(148,163,184,0.2)', borderRadius: 8, padding: '14px 22px', color: '#94a3b8', fontSize: 22, fontWeight: 700},
  archPanels: {display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28},
  archPanel: {backgroundColor: 'rgba(255,255,255,0.06)', border: '1px solid rgba(148,163,184,0.22)', borderRadius: 12, padding: '26px 24px', display: 'grid', gap: 12},
  archPanelAccent: {backgroundColor: 'rgba(94,234,212,0.06)', border: '1px solid rgba(94,234,212,0.22)'},
  archPanelLabel: {color: '#ffffff', fontSize: 28, fontWeight: 950, marginBottom: 6},
  archNode: {display: 'flex', alignItems: 'center', gap: 14, padding: '12px 16px', backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 8},
  archNum: {color: '#5eead4', fontSize: 19, fontWeight: 950, minWidth: 26},
  archNodeText: {color: '#e2e8f0', fontSize: 22, fontWeight: 800},
  demoLayout: {display: 'grid', gridTemplateColumns: '0.65fr 1.35fr', gap: 68, height: '100%', padding: '72px 90px'},
  demoPhoneWrap: {alignSelf: 'center'},
  demoPhoneFrame: {width: '100%', height: 840, border: '16px solid #020617', borderRadius: 50, overflow: 'hidden', position: 'relative', backgroundColor: '#020617', boxShadow: '0 30px 80px rgba(2,6,23,0.5)'},
  demoPhoneImg: {width: '100%', height: '100%', objectFit: 'cover'},
  bbox: {position: 'absolute', top: '20%', left: '12%', right: '12%', bottom: '20%', border: '5px solid #22c55e', borderRadius: 6, boxShadow: '0 0 28px rgba(34,197,94,0.4)'},
  bboxLabel: {position: 'absolute', top: -38, left: -5, backgroundColor: '#22c55e', color: '#04111f', fontSize: 19, fontWeight: 950, padding: '5px 11px'},
  ttsCaption: {position: 'absolute', bottom: 18, left: 14, right: 14, backgroundColor: 'rgba(6,17,31,0.92)', borderRadius: 8, padding: '14px 18px', color: '#ffffff', fontSize: 24, fontWeight: 900},
  demoRight: {alignSelf: 'center', display: 'grid', gap: 28},
  demoCards: {display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14},
  demoCard: {backgroundColor: 'rgba(255,255,255,0.07)', border: '1px solid rgba(148,163,184,0.25)', borderRadius: 10, padding: '20px 22px', display: 'grid', gap: 7},
  demoCardLabel: {color: '#94a3b8', fontSize: 19, fontWeight: 800},
  demoCardVal: {fontSize: 32, fontWeight: 950},
  ttsBox: {backgroundColor: 'rgba(255,255,255,0.07)', border: '1px solid rgba(94,234,212,0.3)', borderRadius: 10, padding: '22px 26px', display: 'grid', gap: 10},
  ttsBoxLabel: {color: '#5eead4', fontSize: 21, fontWeight: 900},
  ttsBoxText: {color: '#ffffff', fontSize: 30, fontWeight: 950},
  feedbackWrap: {padding: '82px 90px', display: 'grid', gap: 44},
  vibGrid: {display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20},
  vibCard: {borderRadius: 12, padding: '30px 22px', textAlign: 'center', display: 'grid', gap: 16, border: '2px solid', backgroundColor: 'rgba(255,255,255,0.06)'},
  vibBadge: {borderRadius: 6, padding: '10px 0', color: '#06111f', fontSize: 22, fontWeight: 950},
  vibScore: {color: '#e2e8f0', fontSize: 21, fontWeight: 800},
  vibDesc: {color: '#94a3b8', fontSize: 19, fontWeight: 700},
  speechCard: {backgroundColor: 'rgba(255,255,255,0.08)', border: '1px solid rgba(94,234,212,0.3)', borderRadius: 12, padding: '28px 34px', display: 'grid', gap: 12},
  speechLabel: {color: '#5eead4', fontSize: 21, fontWeight: 900},
  speechText: {color: '#ffffff', fontSize: 36, fontWeight: 950},
  speechNote: {color: '#94a3b8', fontSize: 21, fontWeight: 800},
  uploadWrap: {padding: '92px 90px', display: 'grid', gap: 40},
  flowRow: {display: 'flex', alignItems: 'center', gap: 22},
  flowBoxA: {flex: 1, borderRadius: 12, padding: '26px 22px', textAlign: 'center', border: '2px solid rgba(99,160,255,0.5)', backgroundColor: 'rgba(15,43,76,0.4)'},
  flowBoxS: {flex: 1, borderRadius: 12, padding: '26px 22px', textAlign: 'center', border: '2px solid rgba(94,234,212,0.4)', backgroundColor: 'rgba(15,118,110,0.2)'},
  flowBoxD: {flex: 1, borderRadius: 12, padding: '26px 22px', textAlign: 'center', border: '2px solid rgba(167,139,250,0.4)', backgroundColor: 'rgba(91,33,182,0.2)'},
  flowArrow: {display: 'flex', alignItems: 'center', justifyContent: 'center'},
  arrowText: {color: '#5eead4', fontSize: 42, fontWeight: 900},
  flowLabel: {color: '#ffffff', fontSize: 26, fontWeight: 950, marginBottom: 6},
  flowSub: {color: '#94a3b8', fontSize: 20, fontWeight: 700},
  apiTable: {display: 'grid', gap: 12},
  apiRow: {display: 'grid', gridTemplateColumns: '76px 240px 1fr 1fr', gap: 16, alignItems: 'center', backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 10, padding: '16px 22px', boxShadow: '0 6px 20px rgba(15,23,42,0.06)'},
  apiMethod: {color: '#ffffff', fontSize: 17, fontWeight: 950, padding: '6px 8px', borderRadius: 6, textAlign: 'center'},
  apiPath: {color: '#0f2b4c', fontSize: 20, fontWeight: 900, fontFamily: 'monospace'},
  apiDesc: {color: '#334155', fontSize: 20, fontWeight: 750},
  apiDetail: {color: '#64748b', fontSize: 17, fontWeight: 700, fontFamily: 'monospace'},
  verifyWrap: {display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, height: '100%', padding: '110px 90px'},
  verifySection: {fontSize: 24, fontWeight: 900, marginBottom: 14, marginTop: 32},
  verifyRow: {display: 'grid', gridTemplateColumns: '1fr 1fr', borderBottom: '1px solid #e2e8f0', padding: '16px 0', gap: 14},
  verifyKey: {color: '#64748b', fontSize: 23, fontWeight: 800},
  verifyVal: {color: '#0f2b4c', fontSize: 25, fontWeight: 950},
  verifyPending: {color: '#475569', fontSize: 22, fontWeight: 750, padding: '12px 16px', backgroundColor: '#fff7ed', borderRadius: 8, marginBottom: 8},
  trialsWrap: {padding: '82px 90px', display: 'grid', gap: 40},
  trialsGrid: {display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 22},
  trialCard: {backgroundColor: 'rgba(255,255,255,0.06)', border: '1px solid rgba(148,163,184,0.26)', borderRadius: 12, padding: '28px 26px', display: 'grid', gap: 14},
  trialProblem: {color: '#f87171', fontSize: 25, fontWeight: 950},
  trialLesson: {color: '#e2e8f0', fontSize: 21, fontWeight: 800, lineHeight: 1.4},
  trialDir: {color: '#5eead4', fontSize: 21, fontWeight: 800, lineHeight: 1.4},
  closingWrap: {position: 'absolute', top: 160, left: 140, right: 140, textAlign: 'center'},
};
