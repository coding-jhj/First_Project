# VoiceGuide MVP 실행 가이드

## 사전 준비

- Python 3.10+
- Android Studio
- Android 폰 (USB 케이블)
- ngrok 계정 (무료) → [ngrok.com](https://ngrok.com) 가입

---

## 1단계: 코드 받기

```cmd
git clone https://github.com/coding-jhj/VoiceGuide.git
cd VoiceGuide
```

---

## 2단계: Python 패키지 설치

```cmd
pip install -r requirements.txt
pip install ultralytics
```

> 첫 실행 시 YOLO 모델(yolo11n.pt)이 자동 다운로드됩니다. (약 1분, 인터넷 필요)

---

## 3단계: ngrok 설치

1. [https://ngrok.com/download](https://ngrok.com/download) 에서 Windows용 다운로드
2. 압축 해제 후 `C:\ngrok` 폴더에 `ngrok.exe` 저장
3. ngrok 대시보드에서 본인 토큰 확인 후 연결

```cmd
ngrok config add-authtoken 본인토큰
```

---

## 4단계: 서버 실행

터미널을 **2개** 열어서 각각 실행합니다.

**터미널 1 - FastAPI 서버:**
```cmd
cd VoiceGuide
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
→ `Uvicorn running on http://0.0.0.0:8000` 뜨면 성공. 창 닫지 말 것.

**터미널 2 - ngrok 터널:**
```cmd
set PATH=%PATH%;C:\ngrok
ngrok http 8000
```
→ `Forwarding https://xxxx.ngrok-free.app` URL 복사해 두기

---

## 5단계: Android 앱 설치

1. Android Studio 실행
2. `Open` → `VoiceGuide/android` 폴더 선택
3. Gradle sync 완료 대기 (첫 실행 약 3~5분)
4. 폰을 USB로 PC에 연결
5. 폰에서 USB 디버깅 활성화
   - 설정 → 휴대전화 정보 → 소프트웨어 정보 → **빌드번호 7번 탭**
   - 설정 → 개발자 옵션 → **USB 디버깅 ON**
   - USB 연결 후 팝업 → **허용**
6. Android Studio 상단에서 기기 선택 후 ▶ **Run**

---

## 6단계: 앱 사용

1. 앱 실행 후 URL 입력란에 **ngrok URL** 붙여넣기
   - 예: `https://xxxx.ngrok-free.app`
2. **분석 시작** 버튼 탭
3. 카메라가 켜지며 3초마다 자동 분석 + 음성 안내 시작
4. **분석 중지** 버튼으로 정지

---

## 주의사항

| 항목 | 내용 |
|------|------|
| ngrok URL | 재실행할 때마다 URL이 바뀜 → 앱에 새 URL 다시 입력 |
| 네트워크 | 서버 PC와 폰이 같은 Wi-Fi 불필요 (ngrok이 중계) |
| 볼륨 | 음성 안내는 미디어 볼륨으로 출력됨 → 미디어 볼륨 확인 |
| 서버 유지 | 터미널 1, 2는 데모 중 계속 켜져 있어야 함 |
