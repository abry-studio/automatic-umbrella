import os
from google import genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

def analyze_image(image_path):
    """
    이미지를 받아 Gemini Vision API를 통해 형태, 특징, 브랜드 등을 텍스트로 추출합니다.
    """
    try:
        # API 키는 환경변수 GEMINI_API_KEY에서 자동으로 읽어옵니다.
        client = genai.Client()
        image = Image.open(image_path)
        
        prompt = "이 이미지에 있는 제품의 형태, 주요 특징, 그리고 브랜드를 분석해서 자세히 한국어로 설명해줘."
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image]
        )
        return response.text
    except Exception as e:
        return f"이미지 분석 중 오류가 발생했습니다: {e}"
