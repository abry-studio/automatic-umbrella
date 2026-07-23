from google import genai
import os

def analyze_shorts(transcript, image_info=None):
    client = genai.Client()
    
    prompt = f"""
다음은 유튜브 쇼츠 영상에서 추출한 자막입니다:
{transcript}
"""
    if image_info and "오류" not in image_info:
        prompt += f"\n추가로, 영상 속 제품에 대한 이미지 분석 내용입니다:\n{image_info}\n"
        
    prompt += """
위 정보를 바탕으로 다음 3가지 모듈에 대한 분석을 작성해주세요. 출력 형식은 마크다운(Markdown)으로 깔끔하게 정리해주세요.

[모듈 1: 시장성 및 가격 분석 (Marketability & Pricing Analysis)]
- 예상 가격대 및 가치 (Estimated Price & Value): 제품이 판매 가능한지, 충동구매(예: 8만원 이하) 혹은 고가치 제품인지 분석
- 시장성 (Market Viability): 소비자의 페인포인트를 해결하는지, 전환 잠재력이 높은지 평가하여 크리에이터가 안 팔릴 제품에 시간을 낭비하지 않도록 진단.

[모듈 2: 마케팅 및 세일즈 퍼널 분석 (Marketing & Sales Funnel Analysis)]
- What (무엇을): 핵심 제품이나 숨겨진 제안(Offer)
- How (어떻게): 오프닝 훅(Hook), 스토리텔링 구조, CTA 분석
- Why (왜 팔리는가 - 심리/타겟): 주요 타겟 인구통계 및 심리적 트리거
- Why Buy (왜 사야 하는지 - 구매 동기): 핵심 소비자 혜택, 해결되는 페인포인트, 지갑을 여는 결정적 이유를 명확히 정의

[모듈 3: 맞춤형 AI 스크립트 재작성 (Custom AI Script Rewriter)]
- 시니어/중장년층(Mature/Senior) 타겟을 위해 기존 자막을 완전히 새롭고 독창적인 스크립트로 재작성해주세요.
- 예의 바르면서도 흡입력 있는 스토리텔링, 강력한 훅을 포함하세요.
- Vrew나 CapCut 같은 프로그램에 바로 복사해서 더빙에 사용할 수 있도록 화자나 효과음 지시문 없이 '순수 대본 텍스트' 형식으로 깔끔하게 포맷팅해주세요.
"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"분석 중 오류가 발생했습니다: {e}"
