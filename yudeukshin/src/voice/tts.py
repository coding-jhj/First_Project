import os
import hashlib
import html
from dotenv import load_dotenv

load_dotenv()

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__tts_cache__")
os.makedirs(_CACHE_DIR, exist_ok=True)

_api_key  = os.getenv("AZURE_SPEECH_KEY")
_region   = os.getenv("AZURE_SPEECH_REGION", "koreacentral")
_hf_token = os.getenv("HF_TOKEN", "")


def _cache_path(text: str, mode: str = "normal") -> str:
    key = hashlib.md5(f"tts_{text}_{mode}".encode("utf-8")).hexdigest()
    return os.path.join(_CACHE_DIR, f"{key}.wav")


def _build_ssml(text: str, mode: str) -> str:
    rate = "1.2" if mode == "critical" else "1.1"
    safe_text = html.escape(text, quote=False)
    return f"""
<speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='ko-KR'>
    <voice name='ko-KR-SoonBokNeural'>
        <mstts:silence type="Sentenceboundary" value="20ms"/>
        <mstts:silence type="Comma" value="20ms"/>
        <prosody rate='{rate}'>
            {safe_text}
        </prosody>
    </voice>
</speak>
"""


def _generate_azure(text: str, path: str, mode: str = "normal") -> bool:
    """Azure TTS로 wav 파일 생성. azure-cognitiveservices-speech 미설치 시 건너뜀."""
    if not _api_key:
        return False
    if not text or not text.strip():
        text = "안내할 내용이 없습니다."
    if os.path.exists(path):
        return True
    try:
        # 최상단 import 대신 lazy import — 패키지 없는 환경(Cloud Run 기본)에서 서버 구동 유지
        import azure.cognitiveservices.speech as speechsdk  # noqa: PLC0415
        speech_config = speechsdk.SpeechConfig(subscription=_api_key, region=_region)
        speech_config.speech_synthesis_voice_name = "ko-KR-SoonBokNeural"
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )
        audio_config = speechsdk.audio.AudioOutputConfig(filename=path)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )
        result = synthesizer.speak_ssml_async(_build_ssml(text, mode)).get()
        return result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted
    except ImportError:
        print("[TTS] azure-cognitiveservices-speech 미설치 — Azure TTS 건너뜀")
        return False
    except Exception as e:
        print(f"[TTS] Azure 에러: {e}")
        return False


def _generate_qwen3(text: str, path: str) -> bool:
    """Qwen3-TTS via HuggingFace Inference API.

    평균 응답 3~8초 — 실시간 장애물 안내 X, 비실시간 용도 권장.
    HF_TOKEN 환경변수 필요. 무료 티어 1000req/day.
    """
    if not _hf_token or not text or not text.strip():
        return False
    try:
        import requests
        resp = requests.post(
            "https://api-inference.huggingface.co/models/"
            "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            headers={"Authorization": f"Bearer {_hf_token}"},
            json={"inputs": text},
            timeout=20,
        )
        if resp.status_code == 200 and resp.content:
            with open(path, "wb") as f:
                f.write(resp.content)
            return True
        print(f"[TTS] Qwen3 HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"[TTS] Qwen3 에러: {e}")
    return False


def _generate(text: str, path: str, mode: str = "normal") -> bool:
    """TTS 생성. Qwen3(HF_TOKEN 있을 때, critical 제외) → Azure → 실패 순."""
    if os.path.exists(path):
        return True
    if _hf_token and mode != "critical" and _generate_qwen3(text, path):
        return True
    return _generate_azure(text, path, mode)


def warmup_cache() -> None:
    """서버 시작 시 짧은 문장 캐시 생성으로 첫 요청 지연 완화."""
    sample = "음성 안내를 준비했습니다."
    path = _cache_path(sample, mode="normal")
    if not os.path.exists(path):
        _generate(sample, path, mode="normal")


def get_tts_audio(text: str, mode: str = "normal"):
    """TTS 오디오 파일 경로 반환. 없으면 생성."""
    if not text or not text.strip():
        text = "안내할 내용이 없습니다."
    path = _cache_path(text, mode)
    if os.path.exists(path):
        return path
    if _generate(text, path, mode=mode):
        return path
    return None
