import gradio as gr
from youtube_parser import get_youtube_info
from image_processor import analyze_image
from analyzer import analyze_shorts
from tts_generator import create_tts
from video_generator import create_video
import re
import pandas as pd
from datetime import datetime
import os
import zipfile

def extract_script(analysis_result):
    script_text = ""
    if "모듈 3" in analysis_result:
        script_part = analysis_result.split("모듈 3")[-1]
        lines = script_part.split('\n')[1:]
        script_text = '\n'.join(lines).strip()
        
    script_text = re.sub(r'<[^>]+>', '', script_text)
    clean_script = re.sub(r'[*#_\[\]\-]', '', script_text).strip()
    return clean_script

def process_batch_data(urls_text, source_video, image_files, bgm_file, script_type, slow_tts):
    urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
    
    # 소스 비디오가 없고 URL도 없으면 에러
    if not urls and not source_video:
        return "분석할 유튜브 URL이나 영상 파일을 넣어주세요.", None, None, None
        
    script_mode = "15_sec" if "15초" in script_type else "standard"
    
    results = []
    all_markdown_output = ""
    audio_files = []
    video_files = []
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"output_{timestamp}"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. 로컬 소스 비디오가 있으면 우선 처리
    if source_video:
        title = "로컬_업로드_영상"
        all_markdown_output += f"## 🎬 [로컬 업로드 영상 분석]\n"
        
        # 비디오는 transcript가 없지만 비디오 자체를 넘깁니다.
        image_info = None
        first_image = image_files[0] if image_files else None
        if first_image:
            image_info = analyze_image(first_image)
            if "오류" in image_info:
                image_info = None
                
        analysis_result = analyze_shorts("", image_info=image_info, script_type=script_mode, video_path=source_video)
        all_markdown_output += analysis_result + "\n\n---\n"
        
        clean_script = extract_script(analysis_result)
        
        if clean_script:
            safe_title = title
            audio_filename = f"{out_dir}/음성_로컬_{safe_title}.mp3"
            tts_path = create_tts(clean_script, filename=audio_filename, lang='ko', slow=slow_tts)
            video_filename = ""
            if tts_path:
                audio_files.append(tts_path)
                if image_files:
                    video_filename = f"{out_dir}/영상_로컬_{safe_title}.mp4"
                    video_path = create_video(image_files, tts_path, output_path=video_filename, script_text=clean_script, bgm_path=bgm_file)
                    if video_path:
                        video_files.append(video_path)
                        
            results.append({
                "작업날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "유튜브_주소": "로컬 영상 업로드",
                "제목": title,
                "상태": "성공",
                "분석결과": analysis_result,
                "추출대본": clean_script,
                "생성된_음성": os.path.basename(audio_filename) if clean_script else "",
                "생성된_영상": os.path.basename(video_filename) if (clean_script and image_files) else ""
            })
            
    # 2. 기존 URL 배치 처리
    for i, url in enumerate(urls):
        all_markdown_output += f"## 🎬 [{i+1}번 유튜브 영상 분석]({url})\n"
        
        info = get_youtube_info(url)
        title = info.get("title", f"영상_{i+1}")
        
        if info.get("error"):
            all_markdown_output += f"❌ 파싱 오류: {info['error']}\n\n---\n"
            results.append({"URL": url, "제목": title, "상태": "파싱 오류", "분석결과": info['error'], "추출대본": ""})
            continue
            
        transcript = info.get("transcript", "")
        if not transcript or "자막을 가져올 수 없습니다" in transcript:
            all_markdown_output += f"⚠️ 자막 추출 실패 (제목: {title})\n\n---\n"
            results.append({"URL": url, "제목": title, "상태": "자막 추출 실패", "분석결과": "", "추출대본": ""})
            continue
            
        image_info = None
        # 분석용 이미지는 첫 번째 이미지만 사용
        first_image = image_files[0] if image_files else None
        if first_image and i == 0:
            image_info = analyze_image(first_image)
            if "오류" in image_info:
                image_info = None
                
        analysis_result = analyze_shorts(transcript, image_info, script_type=script_mode)
        all_markdown_output += analysis_result + "\n\n---\n"
        
        clean_script = extract_script(analysis_result)
        
        if clean_script:
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:20]
            audio_filename = f"{out_dir}/음성_{i+1}_{safe_title}.mp3"
            tts_path = create_tts(clean_script, filename=audio_filename, lang='ko', slow=slow_tts)
            if tts_path:
                audio_files.append(tts_path)
                # 사용자가 이미지를 업로드했다면, 오디오/BGM/자막과 결합하여 MP4 자동 생성
                if image_files:
                    video_filename = f"{out_dir}/영상_{i+1}_{safe_title}.mp4"
                    video_path = create_video(image_files, tts_path, output_path=video_filename, script_text=clean_script, bgm_path=bgm_file)
                    if video_path:
                        video_files.append(video_path)
                
        results.append({
            "작업날짜": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "유튜브_주소": url,
            "제목": title,
            "상태": "성공",
            "분석결과": analysis_result,
            "추출대본": clean_script,
            "생성된_음성": os.path.basename(audio_filename) if clean_script else "",
            "생성된_영상": os.path.basename(video_filename) if (clean_script and image_files) else ""
        })
        
    excel_path = f"{out_dir}/분석결과_{timestamp}.xlsx"
    df = pd.DataFrame(results)
    df.to_excel(excel_path, index=False)
    
    zip_path = f"쇼츠분석_압축_{timestamp}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(excel_path, arcname=os.path.basename(excel_path))
        for audio in audio_files:
            zipf.write(audio, arcname=os.path.basename(audio))
        for video in video_files:
            zipf.write(video, arcname=os.path.basename(video))
            
    preview_audio = audio_files[-1] if audio_files else None
    preview_video = video_files[-1] if video_files else None

    return all_markdown_output, preview_audio, preview_video, zip_path

with gr.Blocks(title="유튜브 쇼츠 제품/시장성 분석기", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🚀 궁극의 쇼츠 자동 매칭 및 비디오 공장")
    gr.Markdown("복잡한 캡컷(CapCut)은 이제 안녕! 유튜브 주소나 내 영상을 넣으면, 사진과 음악이 곁들여진 **최종 영상(MP4)**을 1분 만에 뽑아드립니다.")
    
    with gr.Tabs():
        with gr.Tab("1. 🎬 원본(소스) 입력"):
            gr.Markdown("### AI가 분석하고 베껴올 타겟 영상(원본)을 선택하세요.")
            with gr.Row():
                with gr.Column():
                    yt_input = gr.Textbox(label="유튜브 쇼츠 URL 리스트", lines=4, placeholder="여기에 주소를 넣거나, 우측에 영상을 직접 올리세요.")
                with gr.Column():
                    source_video = gr.Video(label="내 PC 원본 영상 업로드 (유튜브 주소 대신 사용)", interactive=True)
                    
        with gr.Tab("2. 🖼️ 생성 옵션 (사진/음악)"):
            gr.Markdown("### 숏폼 영상으로 뽑아낼 사진과 배경음악을 세팅하세요.")
            with gr.Row():
                img_input = gr.File(file_count="multiple", label="제품 이미지 갤러리 (다중 업로드 지원)")
                bgm_input = gr.File(label="배경음악(BGM) MP3 업로드 (선택사항)")
                
        with gr.Tab("3. ⚙️ 대본 및 AI 설정"):
            with gr.Row():
                script_type_input = gr.Radio(
                    choices=["📝 표준/전체 대본 (Standard Full Script)", "🛒 15초 쇼핑/커머스 전용 대본 (15-Sec Shopping Shorts)"],
                    value="🛒 15초 쇼핑/커머스 전용 대본 (15-Sec Shopping Shorts)",
                    label="대본 생성 모드"
                )
                tts_speed = gr.Checkbox(label="음성 속도 느리게 (중장년층 친화적)", value=False)
                
    analyze_btn = gr.Button("🔥 대본 분석 및 최종 숏폼 영상 제작하기", variant="primary", size="lg")
    
    with gr.Accordion("결과물 확인 (클릭해서 열기)", open=True):
        with gr.Row():
            with gr.Column(scale=2):
                result_output = gr.Markdown(label="분석 결과 요약")
            with gr.Column(scale=1):
                audio_output = gr.Audio(label="대본 음성 (TTS)", type="filepath", interactive=False)
                video_output = gr.Video(label="최종 완성본 (사진+음성+자막)", interactive=False)
                download_output = gr.File(label="📦 모든 파일 일괄 다운로드 (ZIP)")
            
    analyze_btn.click(
        fn=process_batch_data, 
        inputs=[yt_input, source_video, img_input, bgm_input, script_type_input, tts_speed], 
        outputs=[result_output, audio_output, video_output, download_output]
    )

if __name__ == "__main__":
    app.launch(inbrowser=True)
