from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

def get_youtube_info(url):
    """
    유튜브 URL을 받아 메타데이터(제목, 설명)와 자막을 추출합니다.
    """
    result = {
        "title": "",
        "description": "",
        "transcript": "",
        "error": None
    }
    
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            result["title"] = info.get('title', '')
            result["description"] = info.get('description', '')
            video_id = info.get('id', '')
            
            if video_id:
                try:
                    # 한국어, 영어 순서로 자막 가져오기 시도
                    transcript_list = YouTubeTranscriptApi().fetch(video_id, languages=['ko', 'en'])
                    transcript_text = " ".join([t.text for t in transcript_list])
                    result["transcript"] = transcript_text
                except Exception as e:
                    result["transcript"] = f"자막을 가져올 수 없습니다. (이유: {e})"
            
    except Exception as e:
        result["error"] = f"유튜브 정보 추출 중 오류가 발생했습니다: {e}"
        
    return result
