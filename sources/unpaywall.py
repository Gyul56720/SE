"""
Unpaywall API 클라이언트. DOI로 저작권자가 스스로 공개한 합법 오픈액세스 사본
(저자 self-archive, 출판사 무료 배포본, 리포지토리 미러 등)을 조회한다.

로그인/크리덴셜을 쓰지 않는다 -- email 파라미터는 무료 API 이용 약관상 요구되는
사용자 식별용 연락처일 뿐 계정 인증이 아니다. Sci-Hub/LibGen 같은 불법 사이트와 달리
저작권 침해 없이 합법적으로 공개된 사본만 찾아준다. 못 찾으면 조용히 None을 반환한다
(대부분의 유료 저널 논문은 애초에 오픈액세스 사본이 없는 게 정상 상황이라 에러로 취급하지 않음).
"""

from __future__ import annotations
import requests

from config import UNPAYWALL_EMAIL

BASE = "https://api.unpaywall.org/v2"


def find_oa_pdf_url(doi: str) -> str | None:
    """DOI로 합법 오픈액세스 PDF URL을 찾는다. UNPAYWALL_EMAIL이 없거나 못 찾으면 None."""
    if not doi or not UNPAYWALL_EMAIL:
        return None
    doi_clean = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    try:
        resp = requests.get(f"{BASE}/{doi_clean}", params={"email": UNPAYWALL_EMAIL}, timeout=15)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    best = data.get("best_oa_location") or {}
    return best.get("url_for_pdf") or best.get("url")


if __name__ == "__main__":
    # 잘 알려진 오픈액세스 논문 DOI로 동작 확인
    print(find_oa_pdf_url("10.1038/nphys1170"))
