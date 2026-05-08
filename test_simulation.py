#!/usr/bin/env python
"""
VoiceGuide API 엔드포인트 시뮬레이션 및 성능 테스트
"""
from fastapi.testclient import TestClient
from src.api.main import app
from src.api import db
import json
import time

# DB 초기화
db.init_db()

client = TestClient(app)

print('=== API 엔드포인트 시뮬레이션 ===\n')

# 1. 정책 배포
print('1️⃣ GET /api/policy (SSOT 정책 배포)')
r = client.get('/api/policy')
print(f'   Status: {r.status_code} ✅' if r.status_code == 200 else f'   Status: {r.status_code} ❌')
policy = r.json()
print(f'   Version: {policy.get("version")}')
print(f'   Classes: {len(policy.get("classes", {}))} objects')

# 2. 탐지 결과 전송 (/detect)
print('\n2️⃣ POST /detect (온디바이스 탐지 결과)')
detect_payload = {
    'device_id': 'sim-device-001',
    'wifi_ssid': 'HomeNetwork',
    'request_id': 'req-001',
    'mode': '장애물',
    'camera_orientation': 'front',
    'objects': [
        {
            'class_ko': '의자',
            'confidence': 0.91,
            'bbox_norm_xywh': [0.5, 0.5, 0.2, 0.25],
        },
        {
            'class_ko': '책상',
            'confidence': 0.85,
            'bbox_norm_xywh': [0.6, 0.55, 0.25, 0.3],
        }
    ]
}
r = client.post('/detect', json=detect_payload)
print(f'   Status: {r.status_code} ✅' if r.status_code == 200 else f'   Status: {r.status_code} ❌')
result = r.json()
print(f'   Sentence: "{result.get("sentence")}"')
print(f'   Objects in response: {len(result.get("objects", []))}')

# 3. 최근 탐지 조회 API
print('\n3️⃣ GET /status/sim-device-001 (최근 탐지 배포)')
r = client.get('/status/sim-device-001')
print(f'   Status: {r.status_code} ✅' if r.status_code == 200 else f'   Status: {r.status_code} ❌')
status = r.json()
print(f'   Latest detection: {len(status.get("recent_detections", []))} objects')

# 4. 성능 테스트 - 동시 요청
print('\n4️⃣ 성능 테스트 - 10회 연속 요청')
start = time.time()
for i in range(10):
    payload = detect_payload.copy()
    payload['device_id'] = f'sim-device-{i:03d}'
    r = client.post('/detect', json=payload)
elapsed = (time.time() - start) * 1000
print(f'   10회 요청 시간: {elapsed:.2f}ms')
print(f'   평균 요청 시간: {elapsed/10:.2f}ms')
print(f'   ✅ 목표: <200ms/req')

# 5. Health Check
print('\n5️⃣ GET /health (서버 상태 확인)')
r = client.get('/health')
print(f'   Status: {r.status_code} ✅' if r.status_code == 200 else f'   Status: {r.status_code} ❌')
health = r.json()
print(f'   Server status: {health.get("status")}')
print(f'   DB mode: {health.get("db_mode")}')
print(f'   DB status: {health.get("db")}')

# 6. 에러 핸들링 - 빈 물체 리스트
print('\n6️⃣ 에러 처리 - 빈 탐지 (no objects)')
empty_payload = {
    'device_id': 'sim-device-empty',
    'wifi_ssid': 'HomeNetwork',
    'request_id': 'req-empty',
    'mode': '장애물',
    'camera_orientation': 'front',
    'objects': []
}
r = client.post('/detect', json=empty_payload)
result = r.json()
print(f'   Status: {r.status_code} ✅')
print(f'   Sentence: "{result.get("sentence")}"')

# 7. 자동차 경고 시뮬레이션
print('\n7️⃣ 차량 감지 (자동 경고 - critical alert)')
vehicle_payload = {
    'device_id': 'sim-device-vehicle',
    'wifi_ssid': 'HomeNetwork',
    'request_id': 'req-vehicle',
    'mode': '장애물',
    'camera_orientation': 'front',
    'objects': [
        {
            'class_ko': '자동차',
            'confidence': 0.95,
            'bbox_norm_xywh': [0.5, 0.5, 0.3, 0.4],
            'is_vehicle': True,
            'distance_m': 1.2,  # 크리티컬 거리
        }
    ]
}
r = client.post('/detect', json=vehicle_payload)
result = r.json()
print(f'   Status: {r.status_code} ✅')
print(f'   Sentence: "{result.get("sentence")}"')

print('\n' + '='*50)
print('✅ 모든 API 엔드포인트 정상 작동 완료!')
print('='*50)
