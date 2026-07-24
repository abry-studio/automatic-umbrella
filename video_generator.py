from moviepy import ImageClip, AudioFileClip
import os

def create_video(image_path, audio_path, output_path="output_video.mp4"):
    """
    이미지와 음성(TTS) 파일을 결합하여 하나의 영상(MP4)으로 만듭니다.
    """
    if not image_path or not audio_path or not os.path.exists(image_path) or not os.path.exists(audio_path):
        return None
        
    try:
        # 1. 오디오 로드 및 길이 확인
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 2. 이미지 로드 및 오디오 길이에 맞춤
        # MoviePy 2.0 버전 문법 적용 (with_duration, with_audio)
        image_clip = ImageClip(image_path).with_duration(duration)
        
        # 3. 비디오에 오디오 합성
        video_clip = image_clip.with_audio(audio_clip)
        
        # 4. 렌더링 (빠른 속도를 위해 ultrafast 적용)
        video_clip.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            threads=4,
            preset="ultrafast",
            logger=None
        )
        
        # 메모리 해제
        audio_clip.close()
        video_clip.close()
        
        return output_path
    except Exception as e:
        print(f"영상 자동 매칭/생성 중 오류 발생: {e}")
        return None
