from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
import os
import math
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile

def create_text_clip(text, duration, width=1080, height=1920):
    # 투명한 배경의 이미지 생성
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("malgun.ttf", 65) # 맑은 고딕
    except:
        font = ImageFont.load_default()
        
    # 텍스트 크기 계산
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    
    # 텍스트 위치 (가운데 하단)
    x = (width - text_w) // 2
    y = height - 400
    
    # 테두리 (검은색)
    outline_color = "black"
    draw.text((x-3, y-3), text, font=font, fill=outline_color)
    draw.text((x+3, y-3), text, font=font, fill=outline_color)
    draw.text((x-3, y+3), text, font=font, fill=outline_color)
    draw.text((x+3, y+3), text, font=font, fill=outline_color)
    
    # 텍스트 본문 (노란색)
    draw.text((x, y), text, font=font, fill="yellow")
    
    # 임시 파일로 저장 후 ImageClip으로 불러오기 (MoviePy 호환성)
    temp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(temp_dir, f"sub_{hash(text)}.png")
    img.save(tmp_path)
    
    txt_clip = ImageClip(tmp_path).set_duration(duration)
    return txt_clip

def create_video(image_paths, audio_path, output_path="output_video.mp4", script_text="", bgm_path=None):
    """
    여러 장의 이미지와 음성(TTS), 배경음악(BGM), 자막을 결합하여 숏폼 영상을 만듭니다.
    """
    if not image_paths or not audio_path or not os.path.exists(audio_path):
        return None
        
    if isinstance(image_paths, str):
        image_paths = [image_paths]
        
    # 실제로 존재하는 이미지 필터링
    valid_images = [img for img in image_paths if os.path.exists(img)]
    if not valid_images:
        return None

    try:
        # 1. 오디오 로드
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 2. 이미지 슬라이드쇼 구성
        num_images = len(valid_images)
        img_duration = duration / num_images
        
        clips = []
        for img_path in valid_images:
            # 줌인 효과 대신 단순 슬라이드쇼로 묶기 (안정성 확보)
            c = ImageClip(img_path).set_duration(img_duration)
            clips.append(c)
            
        video_clip = concatenate_videoclips(clips, method="compose")
        
        # 3. 배경음악(BGM) 합성
        if bgm_path and os.path.exists(bgm_path):
            bgm_clip = AudioFileClip(bgm_path).volumex(0.1) # BGM 볼륨 10%로 줄이기
            
            # BGM이 더 짧으면 반복, 길면 자르기
            if bgm_clip.duration < duration:
                num_loops = math.ceil(duration / bgm_clip.duration)
                bgm_clip = concatenate_audioclips([bgm_clip] * num_loops).set_duration(duration)
            else:
                bgm_clip = bgm_clip.set_duration(duration)
                
            # 음성과 BGM 합성
            final_audio = CompositeAudioClip([audio_clip, bgm_clip])
            video_clip = video_clip.set_audio(final_audio)
        else:
            video_clip = video_clip.set_audio(audio_clip)
            
        # 4. 자막 생성 및 합성
        if script_text:
            lines = [line.strip() for line in script_text.split('\n') if line.strip()]
            if lines:
                line_duration = duration / len(lines)
                subtitle_clips = []
                for i, line in enumerate(lines):
                    # 너무 긴 줄은 적당히 자르거나 한 줄로 표시
                    if len(line) > 20:
                        line = line[:20] + "\\n" + line[20:]
                    txt_clip = create_text_clip(line, line_duration).set_position(('center', 'center')).set_start(i * line_duration)
                    subtitle_clips.append(txt_clip)
                
                # 영상과 자막 합성
                video_clip = CompositeVideoClip([video_clip] + subtitle_clips)
        
        # 5. 렌더링
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
