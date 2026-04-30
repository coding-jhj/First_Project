import os
import hashlib
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__tts_cache__")
os.makedirs(_CACHE_DIR, exist_ok=True)

def get_tts_audio(text: str, mode: str = "normal"):
    """Azure를 통해 mp3를 생성하고 파일 경로를 반환 (매개변수 최소화)"""
    
    if not text or not text.strip():
        text = "안내할 내용이 없습니다."

    key = hashlib.md5(f"azure_{text}_{mode}".encode("utf-8")).hexdigest()
    path = os.path.join(_CACHE_DIR, f"{key}.mp3")

    if os.path.exists(path):
        return path

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=os.getenv("AZURE_SPEECH_KEY"), 
            region="koreacentral"
        )
        speech_config.speech_synthesis_voice_name = "ko-KR-SoonBokNeural"
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )
        
        audio_config = speechsdk.audio.AudioOutputConfig(filename=path)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        
        rate = "1.2" if mode == "critical" else "1.1"
        ssml = f"""
    <speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" 
           xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='ko-KR'>
        <voice name='ko-KR-SoonBokNeural'>
            <mstts:silence type="Sentenceboundary" value="20ms"/>
            <mstts:silence type="Comma" value="20ms"/>
            <prosody rate='{rate}'>
                {text}
            </prosody>
        </voice>
    </speak>
    """
        
        result = synthesizer.speak_ssml_async(ssml).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return path
        else:
            return None
    except Exception as e:
        print(f"TTS 생성 중 에러 발생: {e}")
        return None