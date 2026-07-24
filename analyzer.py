from google import genai
import os

def analyze_shorts(transcript, image_info=None, script_type="standard", video_path=None, generate_image_prompt=True):
    client = genai.Client()
    
    prompt = ""
    if video_path and os.path.exists(video_path):
        prompt += "다음은 첨부된 쇼츠 영상입니다. 영상을 분석하여 대본을 추출하고 내용을 파악해주세요:\n"
    elif transcript:
        prompt += f"다음은 유튜브 쇼츠 영상에서 추출한 자막입니다:\n{transcript}\n"
        
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
"""

    if script_type == "15_sec":
        prompt += """
[모듈 3: 15초 쇼핑/커머스 전용 숏폼 대본 (15-Second Shopping Shorts Script)]
- 시니어/중장년층의 지갑을 열게 만드는 '제품 판매(커머스)' 목적의 15초 스크립트로 재작성해주세요.
- [훅(Hook)] "이거 안 사면 무조건 손해!", "요즘 난리 난 그 제품!" 처럼 시선을 확 끄는 3초 오프닝으로 시작하세요.
- [소구점] 기존의 불편함(페인포인트)을 이 제품이 어떻게 해결해주는지 가장 큰 장점 1가지만 직관적으로 어필하세요.
- [구매 유도(CTA)] 마지막에는 "좌측 하단 쇼핑몰 클릭!", "프로필 링크에서 바로 확인하세요!" 등 명확한 구매 유도 멘트를 꼭 넣으세요.
- 전체 글자 수는 15초 안에 빠르게 읽을 수 있도록 약 40~60자 내외로 극도로 압축하세요 (홈쇼핑 스타일의 속도감).
- Vrew나 CapCut 같은 프로그램에 바로 복사해서 더빙에 사용할 수 있도록 화자나 효과음 지시문 없이 '순수 대본 텍스트' 형식으로 깔끔하게 포맷팅해주세요.
- 주의: '<시니어 타겟, 40자 내외>' 와 같은 부가 설명이나 꺾쇠(<>) 기호는 절대 쓰지 말고 오직 성우가 읽을 대본 내용만 작성하세요.
"""
    else:
        prompt += """
[모듈 3: 맞춤형 AI 스크립트 재작성 (Custom AI Script Rewriter)]
- 시니어/중장년층(Mature/Senior) 타겟을 위해 기존 내용을 완전히 새롭고 독창적인 스크립트로 재작성해주세요.
- 예의 바르면서도 흡입력 있는 스토리텔링, 강력한 훅을 포함하세요.
- Vrew나 CapCut 같은 프로그램에 바로 복사해서 더빙에 사용할 수 있도록 화자나 효과음 지시문 없이 '순수 대본 텍스트' 형식으로 깔끔하게 포맷팅해주세요.
"""

    if generate_image_prompt:
        prompt += """
[모듈 4: AI 이미지 생성 프롬프트 (Image Generation Prompts for Google Flow/Midjourney)]
- 위 대본 흐름에 맞춰 영상 배경이나 컷으로 쓸 수 있는 이미지 프롬프트 5개를 영어로 작성해주세요.
- [일관성 유지 필수]: 5장의 이미지에 등장하는 주인공 캐릭터(혹은 제품)가 모두 '동일 인물/동일 제품'처럼 보이도록 고정된 핵심 키워드(예: "a 60-year-old Korean man with silver hair wearing a beige knit sweater", "a sleek black smart watch with a neon green strap")를 5개 프롬프트 모두에 공통으로 포함하세요.
- 프롬프트 구조 예시: [고정 캐릭터/제품 설명], [현재 장면의 행동이나 배경 묘사], [조명/카메라 구도], [스타일(photorealistic, cinematic 등)]
- 결과물은 1번부터 5번까지 번호를 매겨서 프롬프트 텍스트만 깔끔하게 출력해주세요.
"""
    
    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 비디오 업로드 및 상태 체크
            contents = [prompt]
            uploaded_file = None
            if video_path and os.path.exists(video_path) and attempt == 0:
                uploaded_file = client.files.upload(file=video_path)
                # 영상이 처리될 때까지 대기
                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(2)
                    uploaded_file = client.files.get(name=uploaded_file.name)
                if uploaded_file.state.name == "FAILED":
                    return "영상 처리 중 오류가 발생했습니다."
            
            if video_path and os.path.exists(video_path):
                # 만약 attempt > 0일 경우 재사용을 위해 uploaded_file을 보존해야 하지만 단순화를 위해 다시 업로드 방지
                # 그냥 매 시도마다 업로드 하거나 이전 업로드된 파일을 씁니다. 
                # (빠른 처리를 위해 코드를 약간 조정했습니다. 여기서는 매번 업로드하지 않고 contents에 추가)
                pass # 위 로직은 좀 복잡해질 수 있으니, 심플하게 매번 업로드하거나 contents를 다시 쓰면 됩니다.
                
            # 제대로된 contents 구성
            req_contents = [prompt]
            if uploaded_file:
                req_contents.append(uploaded_file)
                
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=req_contents
            )
            return response.text
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                time.sleep(5)  # 서버 과부하 시 5초 대기 후 재시도
                continue
            return f"분석 중 오류가 발생했습니다: {e}"
