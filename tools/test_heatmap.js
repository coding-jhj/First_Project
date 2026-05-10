/**
 * test_heatmap.js
 * dashboard.html _haversineM + HEATMAP_RADIUS_M 단위 테스트
 *
 * 실행: node tools/test_heatmap.js
 *
 * 위험 지점: ROUTE "상가옆2" (37.652854, 127.045359)
 *
 * [좌표 선정 근거]
 * simulator.py ROUTE 실측 결과, 출발 "아파트 입구"(37.653404,127.043607)에서
 * 위험지점까지 직선 165.9 m 로 이미 200 m 이내에 해당한다.
 * TC-1 에서는 "200 m 초과 거리" 조건을 검증하기 위해
 * 위험지점에서 정서(正西) 방향 250 m 인 가상 원거리 지점을 사용한다.
 */

// ────────────────────────────────────────────────────
//  dashboard.html 원본 코드 (변경 금지)
// ────────────────────────────────────────────────────
const HEATMAP_RADIUS_M = 200;

function _haversineM(lat1, lng1, lat2, lng2) {
  const R = 6371000, f = Math.PI / 180;
  const phi1 = lat1 * f, phi2 = lat2 * f;
  const dphi = (lat2 - lat1) * f, dlam = (lng2 - lng1) * f;
  const a = Math.sin(dphi/2)**2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dlam/2)**2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ────────────────────────────────────────────────────
//  테스트 유틸
// ────────────────────────────────────────────────────
let passed = 0, failed = 0;

function assert(condition, label, extra) {
  const tag = condition ? 'PASS' : 'FAIL';
  const sfx = extra ? '  (' + extra + ')' : '';
  console.log('  ' + tag + '  ' + label + sfx);
  if (condition) passed++; else failed++;
}

function lerp(lat1, lng1, lat2, lng2, t) {
  return [lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t];
}

// ────────────────────────────────────────────────────
//  기준 좌표
// ────────────────────────────────────────────────────
const DANGER_LAT = 37.652854, DANGER_LNG = 127.045359;  // "상가옆2" 위험지점
// 위험지점에서 정서 250 m: 경도 차 = 250 / (111195 * cos(lat))
const FAR_LAT    = DANGER_LAT;
const FAR_LNG    = DANGER_LNG - 250 / (111195 * Math.cos(DANGER_LAT * Math.PI / 180));

console.log('============================================================');
console.log(' dashboard.html 히트맵 근접 로직 단위 테스트');
console.log('============================================================');
console.log('  위험 지점 : (' + DANGER_LAT + ', ' + DANGER_LNG + ')  "상가옆2"');
console.log('  원거리 기점: (' + DANGER_LAT + ', ' + FAR_LNG.toFixed(6) + ')  위험지점에서 정서 250 m');
console.log('  HEATMAP_RADIUS_M: ' + HEATMAP_RADIUS_M + ' m');
console.log('');

// ────────────────────────────────────────────────────
//  TC-1: 원거리 지점(250 m) -> 거리 > 200 m  (히트맵 숨김)
// ────────────────────────────────────────────────────
console.log('-- TC-1: 원거리(250 m) 지점에서는 히트맵이 보이지 않아야 한다 --');
{
  const d = _haversineM(FAR_LAT, FAR_LNG, DANGER_LAT, DANGER_LNG);
  console.log('  거리: ' + d.toFixed(1) + ' m');
  assert(d > HEATMAP_RADIUS_M,
    '원거리(' + d.toFixed(1) + ' m) > HEATMAP_RADIUS_M(' + HEATMAP_RADIUS_M + ' m)',
    '히트맵 숨김 조건 충족');
}
console.log('');

// ────────────────────────────────────────────────────
//  TC-2: 원거리 지점에서 위험지점 직전 100 m 위치 -> 거리 <= 200 m (히트맵 표시)
//  선형 보간: t = 1 - 100/totalDist
// ────────────────────────────────────────────────────
console.log('-- TC-2: 위험지점 100 m 앞에서는 히트맵이 보여야 한다 --');
{
  const totalDist = _haversineM(FAR_LAT, FAR_LNG, DANGER_LAT, DANGER_LNG);
  const t = Math.max(0, 1 - 100 / totalDist);
  const [pLat, pLng] = lerp(FAR_LAT, FAR_LNG, DANGER_LAT, DANGER_LNG, t);
  const d = _haversineM(pLat, pLng, DANGER_LAT, DANGER_LNG);
  console.log('  보간 위치: (' + pLat.toFixed(6) + ', ' + pLng.toFixed(6) + ')  t=' + t.toFixed(4));
  console.log('  거리: ' + d.toFixed(1) + ' m');
  assert(d <= HEATMAP_RADIUS_M,
    '직전 100 m 지점(' + d.toFixed(1) + ' m) <= HEATMAP_RADIUS_M(' + HEATMAP_RADIUS_M + ' m)',
    '히트맵 표시 조건 충족');
}
console.log('');

// ────────────────────────────────────────────────────
//  TC-3: 위험지점 통과 후 250 m -> 거리 > 200 m (히트맵 사라짐)
//  방향: 다음 ROUTE 포인트 "큰길1" (37.652790, 127.045507)
// ────────────────────────────────────────────────────
console.log('-- TC-3: 위험지점 250 m 통과 후 히트맵이 사라져야 한다 --');
{
  const NEXT_LAT = 37.652790, NEXT_LNG = 127.045507;
  const dLat = NEXT_LAT - DANGER_LAT;
  const dLng = NEXT_LNG - DANGER_LNG;
  const len  = Math.sqrt(dLat**2 + dLng**2);
  const scale250 = 250 / 111195;
  const pLat = DANGER_LAT + (dLat / len) * scale250;
  const pLng = DANGER_LNG + (dLng / len) * scale250;
  const d = _haversineM(pLat, pLng, DANGER_LAT, DANGER_LNG);
  console.log('  통과 250 m 위치: (' + pLat.toFixed(6) + ', ' + pLng.toFixed(6) + ')');
  console.log('  거리: ' + d.toFixed(1) + ' m');
  assert(d > HEATMAP_RADIUS_M,
    '통과 250 m 지점(' + d.toFixed(1) + ' m) > HEATMAP_RADIUS_M(' + HEATMAP_RADIUS_M + ' m)',
    '히트맵 숨김 조건 충족');
}
console.log('');

// ────────────────────────────────────────────────────
//  TC-4: 기본 정확도 - 서울 위도에서 위도 0.001 deg ~= 111 m
//  이론값: 0.001 * 111195 = 111.195 m
// ────────────────────────────────────────────────────
console.log('-- TC-4: _haversineM 기본 정확도  위도 0.001deg ~= 111 m --');
{
  const baseLat = 37.650000, baseLng = 127.045000;
  const d = _haversineM(baseLat, baseLng, baseLat + 0.001, baseLng);
  const expected = 111.195;
  const tolerance = 2.0;
  console.log('  측정값: ' + d.toFixed(3) + ' m  (이론값: ~' + expected + ' m, 허용 +-' + tolerance + ' m)');
  assert(Math.abs(d - expected) < tolerance,
    '|' + d.toFixed(3) + ' - ' + expected + '| = ' + Math.abs(d - expected).toFixed(3) + ' m < ' + tolerance + ' m',
    'Haversine 정확도 OK');
}
console.log('');

// ────────────────────────────────────────────────────
//  결과 요약
// ────────────────────────────────────────────────────
const total = passed + failed;
console.log('============================================================');
const note = failed > 0 ? '  (' + failed + '개 실패)' : '  (전체 통과)';
console.log(' 결과: ' + passed + '/' + total + ' 통과' + note);
console.log('============================================================');

if (failed > 0) process.exit(1);
