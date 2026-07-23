import os
from image_processor import analyze_image
from youtube_parser import get_youtube_info

def main():
    print("="*50)
    print("Media Analyzer Test Script")
    print("="*50)
    
    # 1. 유튜브 파싱 테스트
    sample_url = "https://www.youtube.com/watch?v=L2G5M02GZ0o"
    print(f"\n[유튜브 파싱 테스트] URL: {sample_url}")
    info = get_youtube_info(sample_url)
    
    if info.get("error"):
        print("오류 발생:", info["error"])
    else:
        print("제목:", info["title"])
        transcript_preview = info["transcript"][:200].replace("\n", " ")
        print(f"자막 미리보기: {transcript_preview} ...")
    
    # 2. 이미지 테스트 (샘플 이미지가 있다면 경로 입력)
    sample_image_path = "sample.jpg"
    print(f"\n[이미지 분석 테스트] 파일: {sample_image_path}")
    
    if os.path.exists(sample_image_path):
        print("이미지를 분석 중입니다. 잠시만 기다려주세요...")
        result = analyze_image(sample_image_path)
        print("결과:\n", result)
    else:
        print(f"'{sample_image_path}' 파일이 없어 이미지 테스트는 건너뜁니다.")
        print("테스트를 원하시면, 이 폴더(media-analyzer) 안에 사진을 'sample.jpg' 이름으로 저장한 후 실행해 주세요.")
        
    print("\n테스트가 완료되었습니다!")
    input("\n[안내] 확인을 마치셨으면 엔터 키를 눌러 창을 닫아주세요...")

if __name__ == "__main__":
    main()
