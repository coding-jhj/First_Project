import os
import hashlib
import html
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__tts_cache__")
os.makedirs(_CACHE_DIR, exist_ok=True)

_api_key = os.getenv("AZURE_SPEECH_KEY")
_region = os.getenv("AZURE_SPEECH_REGION", "koreacentral")


def _cache_path(text: str, mode: str = "normal") -> str:
    key = hashlib.md5(f"azure_{text}_{mode}".encode("utf-8")).hexdigest()
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


def _generate(text: str, path: str, mode: str = "normal") -> bool:
    """Azure를 통해 wav 파일 생성."""
    if not _api_key:
        return False

    if not text or not text.strip():
        text = "안내할 내용이 없습니다."

    if os.path.exists(path):
        return True

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=_api_key,
            region=_region
        )
        speech_config.speech_synthesis_voice_name = "ko-KR-SoonBokNeural"
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )

        audio_config = speechsdk.audio.AudioOutputConfig(filename=path)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

        ssml = _build_ssml(text, mode)
        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return True
        return False
    except Exception as e:
        print(f"TTS 생성 중 에러 발생: {e}")
        return False


def warmup_cache() -> None:
    """서버 시작 시 짧은 문장 캐시 생성으로 첫 요청 지연 완화."""
    sample = "음성 안내를 준비했습니다."
    path = _cache_path(sample, mode="normal")
    if not os.path.exists(path):
        _generate(sample, path, mode="normal")


def get_tts_audio(text: str, mode: str = "normal"):
    """Azure를 통해 wav를 생성하고 파일 경로를 반환."""
    if not text or not text.strip():
        text = "안내할 내용이 없습니다."

    path = _cache_path(text, mode)
    if os.path.exists(path):
        return path
    if _generate(text, path, mode=mode):
        return path
    return None