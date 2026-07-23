from gtts import gTTS
import os

def create_tts(text, filename="script_audio.mp3", lang='ko', slow=False):
    """
    텍스트를 받아 gTTS를 통해 음성 파일로 변환하고 저장합니다.
    """
    if not text or not text.strip():
        return None
        
    try:
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"TTS 변환 중 오류 발생: {e}")
        return None
