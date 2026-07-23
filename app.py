import gradio as gr
from youtube_parser import get_youtube_info
from image_processor import analyze_image
from analyzer import analyze_shorts
from tts_generator import create_tts
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
        return "URL을 하나 이상 입력해주세요.", None, None
        
    script_mode = "15_sec" if "15초" in script_type else "standard"
    
    results = []
    all_markdown_output = ""
    audio_files = []
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"output_{timestamp}"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. 반복해서 URL 처리 (배치 프로세싱)
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
        if image_file and i == 0: # 이미지는 첫 번째 영상에만 참고용으로 적용 (일괄 처리의 한계상)
            image_info = analyze_image(image_file)
            if "오류" in image_info:
                image_info = None
                
        # LLM 분석 수행
        analysis_result = analyze_shorts(transcript, image_info, script_type=script_mode)
        all_markdown_output += analysis_result + "\n\n---\n"
        
        # 스크립트 추출 및 TTS 생성
        clean_script = extract_script(analysis_result)
        
        if clean_script:
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:20]
            audio_filename = f"{out_dir}/audio_{i+1}_{safe_title}.mp3"
            tts_path = create_tts(clean_script, filename=audio_filename, lang='ko', slow=slow_tts)
            if tts_path:
                audio_files.append(tts_path)
                
        results.append({
            "URL": url,
            "제목": title,
            "상태": "성공",
            "분석결과": analysis_result,
            "추출대본": clean_script
        })
        
    # 2. 엑셀 파일 저장
    excel_path = f"{out_dir}/analysis_results_{timestamp}.xlsx"
    df = pd.DataFrame(results)
    df.to_excel(excel_path, index=False)
    
    # 3. 압축(ZIP) 파일 생성
    zip_path = f"shorts_analysis_{timestamp}.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(excel_path, arcname=os.path.basename(excel_path))
        for audio in audio_files:
            zipf.write(audio, arcname=os.path.basename(audio))
            
    # 마지막 오디오 파일을 미리듣기용으로 제공
    preview_audio = audio_files[-1] if audio_files else None

    return all_markdown_output, preview_audio, zip_path

with gr.Blocks(title="유튜브 쇼츠 제품/시장성 분석기") as app:
    gr.Markdown("# 🚀 유튜브 쇼츠 제품 & 시장성 분석기 (다중 URL 엑셀 압축 저장 지원)")
    gr.Markdown("여러 개의 쇼츠 URL을 한 줄씩 입력하면, 전체 영상을 한 번에 분석하고 엑셀 파일과 음성 파일들을 **날짜가 찍힌 압축파일(ZIP)**로 만들어 드립니다.")
    
    with gr.Row():
        with gr.Column(scale=1):
            yt_input = gr.Textbox(label="유튜브 쇼츠 URL 리스트 (한 줄에 한 개씩 입력)", lines=5, placeholder="https://www.youtube.com/shorts/...\nhttps://www.youtube.com/shorts/...")
            img_input = gr.Image(type="filepath", label="제품 이미지 업로드 (선택사항, 첫 영상에만 적용됨)")
            
            script_type_input = gr.Radio(
                choices=["📝 표준/전체 대본 (Standard Full Script)", "🛒 15초 쇼핑/커머스 전용 대본 (15-Sec Shopping Shorts)"],
                value="📝 표준/전체 대본 (Standard Full Script)",
                label="대본 생성 모드 선택"
            )
            tts_speed = gr.Checkbox(label="음성 속도 느리게 (중장년층 친화적)", value=False)
            analyze_btn = gr.Button("🔥 대량 종합 분석 및 압축파일 생성하기", variant="primary")
            
        with gr.Column(scale=2):
            result_output = gr.Markdown(label="분석 결과 요약 (마지막 처리 결과)")
            audio_output = gr.Audio(label="생성된 대본 음성 미리듣기 (마지막 영상 기준)", type="filepath", interactive=False)
            download_output = gr.File(label="📦 모든 결과물 압축파일(엑셀+음성) 다운로드")
            
    analyze_btn.click(
        fn=process_batch_data, 
        inputs=[yt_input, img_input, script_type_input, tts_speed], 
        outputs=[result_output, audio_output, download_output]
    )

if __name__ == "__main__":
    app.launch(inbrowser=True)
