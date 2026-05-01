"""
VoiceGuide TTS 모듈 (서버 / Gradio 데모용)
==========================================
Android 앱은 Android TextToSpeech(OS TTS)를 사용하며 이 파일은 서버 데모 전용.

TTS 속도 기준:
  - 긴급(critical): 빠르게 (안드로이드 setSpeechRate(1.25f))
  - 일반(info):     보통 (setSpeechRate(1.1f))
  - 같은 문장 3~5초 이내 반복 없음 (CLASS_COOLDOWN_MS = 5000)
"""
from dotenv import load_dotenv
import os
import hashlib
import pygame

load_dotenv()  # .env 파일의 환경변수 로드 (ELEVENLABS_API_KEY 등)

_api_key  = os.getenv("ELEVENLABS_API_KEY", "")  # 없으면 gTTS 무료 폴백
_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"   # George (다국어 지원)
_MODEL_ID = "eleven_multilingual_v2"  # 한국어 자연스러운 발음 모델

# 같은 문장 억제 시간 (초) — 중복 발화 방지
_REPEAT_COOLDOWN_SECS = 4.0
_last_spoken: dict[str, float] = {}  # 문장 → 마지막 발화 시각 캐시

# 생성된 MP3 파일 저장 디렉터리 — 같은 문장은 재생성 없이 캐시 파일 재사용
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__tts_cache__")
os.makedirs(_CACHE_DIR, exist_ok=True)  # 디렉터리 없으면 자동 생성


def _cache_path(text: str) -> str:
    # API 키 유무를 prefix에 포함 — ElevenLabs/gTTS 전환 시 캐시 충돌 방지
    prefix = "eleven" if _api_key else "gtts"
    key = hashlib.md5(f"{prefix}_{text}".encode("utf-8")).hexdigest()  # 텍스트 → 고유 파일명
    return os.path.join(_CACHE_DIR, f"{key}.mp3")


def _generate(text: str, path: str) -> bool:
    """ElevenLabs 생성, API 키 없거나 실패하면 gTTS 폴백."""
    if _api_key:
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=_api_key)
            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=_VOICE_ID,
                model_id=_MODEL_ID,
                output_format="mp3_44100_128",  # 44.1kHz, 128kbps MP3 — 품질/용량 균형
            )
            with open(path, "wb") as f:
                for chunk in audio_generator:
                    if chunk:
                        f.write(chunk)  # 스트리밍 청크 단위 저장
            return True
        except Exception as e:
            print(f"[TTS] ElevenLabs 오류, gTTS 폴백: {e}")

    # gTTS 폴백 — 무료, 인터넷 필요, ElevenLabs보다 자연스러움 낮음
    try:
        from gtts import gTTS
        gTTS(text, lang="ko").save(path)
        return True
    except Exception as e:
        print(f"[TTS] gTTS 오류: {e}")
        return False


def speak(text: str):
    import time
    # 같은 문장이 4초 이내에 이미 발화됐으면 건너뜀 (경고 피로 방지)
    now = time.monotonic()
    if text in _last_spoken and (now - _last_spoken[text]) < _REPEAT_COOLDOWN_SECS:
        return
    _last_spoken[text] = now  # 발화 시각 기록

    path = _cache_path(text)
    if not os.path.exists(path):
        # 캐시 파일 없으면 새로 생성
        if not _generate(text, path):
            return
    try:
        pygame.mixer.init()             # 오디오 시스템 초기화
        pygame.mixer.music.load(path)   # MP3 파일 로드
        pygame.mixer.music.play()
        # 재생 완료까지 대기 (동기 재생 — Gradio 데모에서 TTS 겹침 방지)
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()     # 파일 잠금 해제 (Windows 필수)
    except Exception as e:
        print(f"[TTS] 재생 오류: {e}")


def warmup_cache():
    """서버 시작 시 자주 쓰는 문장 미리 캐싱 — 첫 요청 지연 방지."""
    # 현재 미구현 — 필요 시 자주 쓰는 문장 목록을 _generate()로 미리 생성할 것
    pass
