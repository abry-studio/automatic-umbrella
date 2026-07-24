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

def process_batch_data(urls_text, image_file, script_type, slow_tts):
    urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
    
    if not urls:
        return "URL을 하나 이상 입력해주세요.", None, None, None
        
    script_mode = "15_sec" if "15초" in script_type else "standard"
    
    results = []
    all_markdown_output = ""
    audio_files = []
    video_files = []
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"output_{timestamp}"
    os.makedirs(out_dir, exist_ok=True)
    
    for i, url in enumerate(urls):
        all_markdown_output += f"## 🎬 [{i+1}번 영상 분석]({url})\n"
        
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
        if image_file and i == 0:
            image_info = analyze_image(image_file)
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
                # 만약 사용자가 이미지를 업로드했다면, 오디오와 결합하여 MP4 영상 자동 생성 (캡컷 기능 대체)
                if image_file:
                    video_filename = f"{out_dir}/영상_{i+1}_{safe_title}.mp4"
                    video_path = create_video(image_file, tts_path, output_path=video_filename)
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
            "생성된_영상": os.path.basename(video_filename) if (clean_script and image_file) else ""
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

with gr.Blocks(title="유튜브 쇼츠 제품/시장성 분석기") as app:
    gr.Markdown("# 🚀 유튜브 쇼츠 자동 매칭 및 대량 분석기 (비디오 자동 생성)")
    gr.Markdown("쇼츠 URL과 제품 사진(옵션)을 넣으면 분석, 대본 작성, TTS 음성 생성에 이어 **사진과 음성을 합성한 최종 영상(MP4)**까지 한 번에 만들어서 ZIP으로 압축해 드립니다! (캡컷 없이 바로 업로드 가능)")
    
    with gr.Row():
        with gr.Column(scale=1):
            yt_input = gr.Textbox(label="유튜브 쇼츠 URL 리스트 (한 줄에 한 개씩 입력)", lines=5, placeholder="https://www.youtube.com/shorts/...\nhttps://www.youtube.com/shorts/...")
            img_input = gr.Image(type="filepath", label="제품 이미지 업로드 (자동 영상 제작에 사용됨)")
            
            script_type_input = gr.Radio(
                choices=["📝 표준/전체 대본 (Standard Full Script)", "🛒 15초 쇼핑/커머스 전용 대본 (15-Sec Shopping Shorts)"],
                value="📝 표준/전체 대본 (Standard Full Script)",
                label="대본 생성 모드 선택"
            )
            tts_speed = gr.Checkbox(label="음성 속도 느리게 (중장년층 친화적)", value=False)
            analyze_btn = gr.Button("🔥 대량 종합 분석 및 영상/음성 압축파일 생성하기", variant="primary")
            
        with gr.Column(scale=2):
            result_output = gr.Markdown(label="분석 결과 요약 (마지막 처리 결과)")
            with gr.Row():
                audio_output = gr.Audio(label="생성된 대본 음성 미리듣기", type="filepath", interactive=False)
                video_output = gr.Video(label="자동 완성된 숏폼 영상 미리보기 (이미지+음성)", interactive=False)
            download_output = gr.File(label="📦 모든 결과물 압축파일(엑셀+음성+영상) 다운로드")
            
    analyze_btn.click(
        fn=process_batch_data, 
        inputs=[yt_input, img_input, script_type_input, tts_speed], 
        outputs=[result_output, audio_output, video_output, download_output]
    )

if __name__ == "__main__":
    app.launch(inbrowser=True)
