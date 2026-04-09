import os
import asyncio
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import telegram

# 1. 암호 불러오기
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. 리포트 수집 함수 (탭 종류에 따라 똑똑하게 작동하도록 수정)
def get_naver_reports(url, report_type):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    table = soup.find('table', {'class': 'type_1'})
    if table is None:
        return [f"{report_type} 데이터를 불러오지 못했습니다."]

    rows = table.find_all('tr')[2:]
    reports = []
    
    for row in rows:
        cols = row.find_all('td')
        
        # [시황정보 탭]은 첫 번째 칸이 '제목', 두 번째가 '증권사'
        if report_type == "시황" and len(cols) >= 2:
            title = cols[0].text.strip()
            firm = cols[1].text.strip()
            if title: reports.append(f"[{firm}] {title}")
            
        # [종목분석 탭]은 첫 칸이 '종목명', 두 번째가 '제목', 여섯 번째가 '증권사'
        elif report_type == "종목" and len(cols) >= 6:
            company = cols[0].text.strip()
            title = cols[1].text.strip()
            firm = cols[5].text.strip()
            if title and company: reports.append(f"[{firm}] {company} - {title}")
            
        if len(reports) == 5: # 각 탭별로 5개씩만 수집
            break
            
    return reports

async def send_telegram_msg(text):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID, 
        text=text, 
        read_timeout=30, write_timeout=30, connect_timeout=30
    )

async def main():
    print("🔍 네이버 증권에서 시황 & 종목 리포트 수집 중...")
    
    # URL 2곳에서 각각 데이터 수집
    market_url = "https://finance.naver.com/research/market_info_list.naver"
    company_url = "https://finance.naver.com/research/company_list.naver"
    
    market_reports = get_naver_reports(market_url, "시황")
    company_reports = get_naver_reports(company_url, "종목")
    
    context = "=== [거시경제: 시황 리포트 Top 5] ===\n" + "\n".join(market_reports) + "\n\n"
    context += "=== [미시경제: 기업/종목 리포트 Top 5] ===\n" + "\n".join(company_reports)

    # 3. 제미나이 심층 분석 지시문 (멀티 데이터 맞춤형)
    prompt = f"""
    당신은 베테랑 경제 전문 기자의 데스크 보고 및 기사 기획을 돕는 수석 어시스턴트입니다. 
    다음은 오늘자 증권사 시황 리포트 5개와 기업/종목 리포트 5개입니다:

    {context}

    위 내용을 바탕으로 다음 세 가지 형식의 보고서를 작성하세요.
    1. [시장 흐름 브리핑]: 시황 리포트를 바탕으로 오늘 거시경제와 증시의 핵심 테마를 3줄로 요약하세요.
    2. [주목할 종목 3선]: 종목 리포트 중 가장 모멘텀이 좋거나 이슈가 될 만한 기업 3곳을 뽑아 '종목명'과 '선정 이유(1줄)'를 적어주세요.
    3. [기사 기획 아이디어]: 위 거시/미시 데이터를 종합하여, 오늘 당장 취재해 볼 만한 매력적인 경제 기사 앵글(제목과 방향성) 1개를 제안해 주세요.

    [중요 작성 규칙]
    - 응답 내용에 `**`, `*`, `_`, `#` 같은 마크다운(Markdown) 서식 기호는 절대로, 단 하나도 사용하지 마세요. (시스템 에러가 발생합니다)
    - 강조가 필요한 부분은 【 】 괄호나 📌, 💡, 🎯, ✍️ 같은 이모지를 활용하여 텍스트로만 깔끔하게 작성하세요.
    """

    print("🧠 제미나이 2.5 플래시가 입체적 분석을 수행 중입니다...")
    response = model.generate_content(prompt)
    result_text = response.text

    final_message = f"📰 【오늘의 증시 & 기업 심층 보고서】\n\n{result_text}"
    await send_telegram_msg(final_message)
    print("✅ 텔레그램 전송이 완료되었습니다!")

if __name__ == "__main__":
    asyncio.run(main())
