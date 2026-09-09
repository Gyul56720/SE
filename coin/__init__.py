"""coin — **뉴스가 뜨면 며칠 뒤에 얼마였나** 를 원장에서 잰다.

    price.py    가격 원장 (일봉)
    news.py     뉴스 원장 (24시간 + 과거)
    tag.py      뉴스 -> 사건 유형 (규칙 사전. LLM 아님)
    null.py     널 모형 -- 기저율. **이 파일이 없으면 나머지는 다 거짓말이다**
    event.py    사건 연구 -- 이 저장소가 메인이라고 부른 자리
    ledger.py   잰것 원장
    prompt.py   원장에서 프롬프트를 짓는다
    ask.py      Gemini
    gate.py     **심판자. LLM 이 아니다**
    loop.py     정제 루프 -- 멈춤 조건이 기계다
    run.py      한 명령
"""
