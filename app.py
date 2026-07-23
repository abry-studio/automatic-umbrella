import gradio as gr
from youtube_parser import get_youtube_info
from image_processor import analyze_image
from analyzer import analyze_shorts

def process_data(url, image_file):
    if not url:
        return "URL을 입력해주세요."
    
    # 1. 유튜브 자막 가져오기
    info = get_youtube_info(url)
    if info.get("error"):
        return f"유튜브 파싱 오류: {info['error']}"
    
    transcript = info.get("transcript", "")
    if not transcript or "자막을 가져올 수 없습니다" in transcript:
        return f"유튜브 자막을 추출할 수 없습니다. 분석이 제한됩니다.\n(제목: {info.get('title')})"
    
    # 2. 이미지 정보 가져오기 (선택사항)
    image_info = None
    if image_file:
        image_info = analyze_image(image_file)
        if "오류" in image_info:
            image_info = f"이미지 분석 실패: {image_info}"
            
    # 3. LLM 종합 분석 수행
    analysis_result = analyze_shorts(transcript, image_info)
    
    return analysis_result

with gr.Blocks(title="유튜브 쇼츠 제품/시장성 분석기") as app:
    gr.Markdown("# 🚀 유튜브 쇼츠 제품 & 시장성 분석기 (Shorts Analyzer)")
    gr.Markdown("쇼츠 URL과 제품 사진(옵션)을 넣으면 시장성 판단, 마케팅 전략 분석, 중장년층 타겟용 대본 재작성을 한 번에 수행합니다.")
    
    with gr.Row():
        with gr.Column(scale=1):
            yt_input = gr.Textbox(label="유튜브 쇼츠 URL 입력", placeholder="https://www.youtube.com/shorts/...")
            img_input = gr.Image(type="filepath", label="제품 이미지 업로드 (선택사항)")
            analyze_btn = gr.Button("🔥 종합 분석 시작하기", variant="primary")
            
        with gr.Column(scale=2):
            result_output = gr.Markdown(label="분석 결과")
            
    analyze_btn.click(
        fn=process_data, 
        inputs=[yt_input, img_input], 
        outputs=result_output
    )

if __name__ == "__main__":
    app.launch(inbrowser=True)
