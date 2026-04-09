import os
import asyncio
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import telegram

# 1. 깃허브 금고(Secrets)에서 암호 불러오기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 2. 제미나이 설정 (최신 2.5 플래시 모델 적용)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def get_market_reports_top10():
    print("🔍 네이버 증권에서 최신 시황 리포트 10개 수집 중...")
    url = "https://finance.naver.com/research/market_info_list.naver"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    table = soup.find('table', {'class': 'type_1'})
    if table is None:
        return ["데이터를 불러오지 못했습니다. 네이버 접속 차단 또는 페이지 구조 변경이 원인일 수 있습니다."]

    rows = table.find_all('tr')[2:]
    
    reports = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 2:
            title = cols[0].text.strip()
            firm = cols[1].text.strip()
            if title:
                reports.append(f"[{firm}] {title}")
            if len(reports) == 10: break
            
    return reports

async def send_telegram_msg(text):
    print("📲 텔레그램으로 브리핑 전송 중...")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    
    # [핵심 수정 1] 텔레그램의 깐깐한 마크다운 검사 기능(parse_mode)을 아예 제거하여 에러 원천 차단
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID, 
        text=text, 
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30
    )

async def main():
    reports_list = get_market_reports_top10()
    context = "\n".join(reports_list)

    # [핵심 수정 2] 제미나이에게 에러를 유발하는 기호를 쓰지 말라고 강력하게 지시
    prompt = f"""
    당신은 베테랑 경제 전문 기자의 데스크 보고 및 기사 기획을 돕는 수석 어시스턴트입니다. 
    다음은 오늘자 주요 증권사 시황 리포트 10개의 제목입니다:

    {context}

    위 내용을 바탕으로 다음 두 가지 형식의 보고서를 작성하세요.
    1. [종합 시황 요약]: 오늘 시장의 핵심 키워드를 3~5개 추출하고, 전체적인 흐름을 약 1000자 내외로 상세히 축약하세요. 
    2. [주요 리포트 5선]: 10개의 리포트 중 가장 시장 영향력이 크거나 눈에 띄는 5개를 선정하여, 각 리포트의 '제목'과 그 리포트가 시사하는 바를 '3줄 요약'으로 정리하세요.

    [중요 작성 규칙]
    - 응답 내용에 `**`, `*`, `_`, `#` 같은 마크다운(Markdown) 서식 기호는 절대로, 단 하나도 사용하지 마세요. (시스템 에러가 발생합니다)
    - 강조가 필요한 부분은 【 】 괄호나 📌, 💡, ➡️ 같은 이모지를 활용하여 순수 텍스트로만 깔끔하게 작성하세요.
    """

    print("🧠 제미나이 2.5 플래시가 대규모 분석을 수행 중입니다...")
    response = model.generate_content(prompt)
    result_text = response.text

    final_message = f"📰 【오늘의 증권 시황 심층 보고서】\n\n{result_text}"
    await send_telegram_msg(final_message)
    print("✅ 모든 작업이 완료되었습니다!")

if __name__ == "__main__":
    asyncio.run(main())
