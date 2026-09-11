"""dig/harvest -- 밖(GitHub · Hugging Face)에서 참고를 끌어와 검증하고 색인한다. 제2의 뇌 2단계.

무엇을 찾나: **자(eval/tasks)가 틀렸다고 한 자리**다. 참고를 줘도 틀린 과제의 깃발이
검색어가 된다(`--틈`). 사람이 `--말` 로 더 줄 수도 있다. 아무 데나 긁지 않는다 -- 눈금이
없는 데를 채워 봐야 값을 하는지 알 길이 없다(eval/tasks 의 이득으로만 안다).

어디서: GitHub 저장소 검색 → README(raw), 토큰이 있으면 코드 검색 → 파일(raw).
Hugging Face 데이터셋·모델 검색 → README(raw). 토큰은 `.env` 의 GITHUB_TOKEN · HF_TOKEN
(없으면 GitHub 은 시간당 60회 안에서, 코드 검색은 건너뛴다). `X-RateLimit-Remaining`
이 0 이거나 403/429 면 그 출처는 **그 바퀴에서 멈추고 그렇다고 말한다** -- 헤더를 바꿔
가며 두드리지 않는다(API 는 곁문이 아니다).

검증 -- 판정은 코드가 한다:
  · 라이선스: SPDX 가 허용 목록(MIT · Apache-2.0 · BSD · ISC · CC0 · CC-BY · MPL …)에
    있어야 저장·색인한다. 미상·비허용은 원장에 '거절' 로만 남긴다
  · 코드(.py): `compile()` 이 되어야 한다 -- 문법이 깨진 조각은 참고가 아니다
  · 요약은 모델이 짓지 않는다. 발췌(코드)다 -- 그래서 대조할 주장이 없다
저장: `dig/corpus/<종류>-<sha12>.md` (gitignore -- 다시 받으면 되는 것, law/corpus 와 같다).
색인: graph/store.적기(요약=발췌, 깃발=코드가 뽑음 + 검색어, 지은이="코드") -- eval/tasks
의 참고가 바로 이 색인을 읽으므로, 다음 `--참고 둘다` 바퀴가 값을 하는지 잰다.
원장: `dig/harvest_ledger.jsonl` append-only (때 · 종류 · url · 파일 · 해시 · 라이선스 ·
검색어 · 판정 · 까닭). 같은 url+해시는 다시 안 받는다. 하루 상한(HARVEST_DAILY_CAP, 기본
200)을 넘으면 멈춘다 -- 24시간 루프가 저장소를 부풀리지 않게.

쓰기:
    python3 dig/harvest.py --틈만                      # 자가 틀린 자리 -> 검색어 (호출 0회)
    python3 dig/harvest.py --틈                        # 그 검색어로 한 바퀴
    python3 dig/harvest.py --말 'cusum change point'   # 사람이 준 말로
    python3 dig/harvest.py --말 x --출처 hf --몇 3 --상한 10
끝값: 0 한 바퀴 돌았다(저장 0 이어도) · 3 못돌림(검색어 없음 · 하루 상한 · 첫 요청부터 막힘)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dig import fetch as FT  # noqa: E402
from graph import night, store  # noqa: E402

말뭉치상대 = "dig/corpus"
원장상대 = "dig/harvest_ledger.jsonl"
파일글자 = 12000
출처들 = ("github", "hf")
허용라이선스 = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "0bsd", "isc", "cc0-1.0",
           "cc-by-4.0", "cc-by-sa-4.0", "cc-by-3.0", "mpl-2.0", "unlicense", "zlib",
           "openrail", "creativeml-openrail-m", "bsl-1.0", "artistic-2.0", "wtfpl"}
막힘코드 = (401, 403, 429)

한번 = None          # 검사가 꽂는다. None 이면 dig.fetch.한번 (검사는 FT.한번 을 바꿔도 된다)


# ---------------------------------------------------------------- 환경
def env값(이름: str, repo=None) -> str:
    """환경 변수, 없으면 .env 의 그 줄. dotenv 없이 -- 값에 `=` 가 있어도 첫 것만 가른다.
    mailer 도 이것을 쓴다(두 벌 금지)."""
    v = os.environ.get(이름, "")
    if v:
        return v
    p = Path(repo or REPO) / ".env"
    if not p.is_file():
        return ""
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith(이름 + "="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return ""


_env = env값          # 옛 이름


def 하루상한() -> int:
    try:
        return int(os.environ.get("HARVEST_DAILY_CAP", "200"))
    except ValueError:
        return 200


# ---------------------------------------------------------------- HTTP
def _받기(url: str, 헤더: dict, 틈: float = 20.0):
    return (한번 or FT.한번)(url, 헤더, 틈)


def _json(url: str, 헤더: dict) -> "tuple[object, object]":
    """(응답, 풀린 JSON 또는 None)."""
    r = _받기(url, 헤더)
    if not r.몸통:
        return r, None
    try:
        return r, json.loads(r.몸통)
    except ValueError:
        return r, None


class 한도:
    """출처마다 '더 두드려도 되나'. 403/429 나 Remaining 0 이면 그 바퀴는 멈춘다."""

    def __init__(self):
        self.막힘: dict = {}

    def 보기(self, 출처: str, r) -> bool:
        if r.코드 in 막힘코드:
            self.막힘[출처] = f"HTTP {r.코드} -- {r.왜[:60] or '한도·권한'}"
            return False
        남 = r.헤더.get("X-RateLimit-Remaining") or r.헤더.get("x-ratelimit-remaining")
        if 남 is not None and str(남).strip() == "0":
            self.막힘[출처] = "X-RateLimit-Remaining 0"
            return False
        return True

    def 되나(self, 출처: str) -> bool:
        return 출처 not in self.막힘


# ---------------------------------------------------------------- 찾기
def _깃허브헤더(repo=None) -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "SE-harvest",
         "X-GitHub-Api-Version": "2022-11-28"}
    tok = env값("GITHUB_TOKEN", repo)
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _허깅헤더(repo=None) -> dict:
    h = {"User-Agent": "SE-harvest"}
    tok = env값("HF_TOKEN", repo)
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def 깃허브찾기(말: str, 몇: int, 한: 한도, repo=None) -> "list[dict]":
    """저장소 검색 -> README raw. 토큰이 있으면 코드 검색 -> 파일 raw 도."""
    h = _깃허브헤더(repo)
    out: list[dict] = []
    q = urllib.parse.quote(f"{말} language:python")
    r, data = _json(f"https://api.github.com/search/repositories?q={q}&sort=stars&per_page={몇}", h)
    if not 한.보기("github", r) or not isinstance(data, dict):
        return out
    for it in (data.get("items") or [])[:몇]:
        full = it.get("full_name") or ""
        lic = ((it.get("license") or {}).get("spdx_id") or "").lower()
        if not full or not 한.되나("github"):
            continue
        hr = dict(h, Accept="application/vnd.github.raw+json")
        rr = _받기(f"https://api.github.com/repos/{full}/readme", hr)
        한.보기("github", rr)
        out.append({"종류": "github-readme", "url": it.get("html_url") or f"https://github.com/{full}",
                    "이름": full, "라이선스": lic, "내용": rr.몸통 if rr.됐나 else "",
                    "별": it.get("stargazers_count", 0), "왜못": "" if rr.됐나 else rr.왜})
    if "Authorization" in h and 한.되나("github"):
        r, data = _json(f"https://api.github.com/search/code?q={q}&per_page={몇}", h)
        if 한.보기("github", r) and isinstance(data, dict):
            for it in (data.get("items") or [])[:몇]:
                rep = it.get("repository") or {}
                full, path = rep.get("full_name") or "", it.get("path") or ""
                if not full or not path.endswith(".py") or not 한.되나("github"):
                    continue
                hr = dict(h, Accept="application/vnd.github.raw+json")
                rr = _받기(f"https://api.github.com/repos/{full}/contents/{urllib.parse.quote(path)}", hr)
                한.보기("github", rr)
                out.append({"종류": "github-code", "url": it.get("html_url") or "",
                            "이름": f"{full}/{path}", "라이선스": "",     # 코드 검색은 라이선스를 안 준다
                            "저장소": full, "내용": rr.몸통 if rr.됐나 else "",
                            "왜못": "" if rr.됐나 else rr.왜})
    # 코드 조각의 라이선스는 저장소 것이다 -- 한 번씩 물어 채운다.
    보인 = {}
    for it in out:
        if it["종류"] == "github-code" and 한.되나("github"):
            full = it["저장소"]
            if full not in 보인:
                r, d = _json(f"https://api.github.com/repos/{full}", h)
                한.보기("github", r)
                보인[full] = (((d or {}).get("license") or {}).get("spdx_id") or "").lower() if isinstance(d, dict) else ""
            it["라이선스"] = 보인[full]
    return out


def _허깅라이선스(it: dict) -> str:
    lic = ((it.get("cardData") or {}).get("license") or "")
    if isinstance(lic, list):
        lic = lic[0] if lic else ""
    if not lic:
        for t in it.get("tags") or []:
            if isinstance(t, str) and t.startswith("license:"):
                lic = t.split(":", 1)[1]
                break
    return str(lic).lower()


def 허깅찾기(말: str, 몇: int, 한: 한도, repo=None) -> "list[dict]":
    h = _허깅헤더(repo)
    out: list[dict] = []
    q = urllib.parse.quote(말)
    for 갈래, 경로 in (("datasets", "datasets/"), ("models", "")):
        if not 한.되나("hf"):
            break
        r, data = _json(f"https://huggingface.co/api/{갈래}?search={q}&limit={몇}&full=true", h)
        if not 한.보기("hf", r) or not isinstance(data, list):
            continue
        for it in data[:몇]:
            rid = it.get("id") or it.get("modelId") or ""
            if not rid or not 한.되나("hf"):
                continue
            rr = _받기(f"https://huggingface.co/{경로}{rid}/raw/main/README.md", h)
            한.보기("hf", rr)
            out.append({"종류": f"hf-{갈래[:-1]}", "url": f"https://huggingface.co/{경로}{rid}",
                        "이름": rid, "라이선스": _허깅라이선스(it),
                        "내용": rr.몸통 if rr.됐나 else "", "왜못": "" if rr.됐나 else rr.왜})
    return out


# ---------------------------------------------------------------- 검증 · 저장 · 색인
def 검증(항목: dict) -> "tuple[bool, str]":
    """(저장해도 되나, 까닭). 판정은 코드가 한다."""
    if not (항목.get("내용") or "").strip():
        return False, "내용 없음" + (f" ({항목.get('왜못')})" if 항목.get("왜못") else "")
    lic = (항목.get("라이선스") or "").lower()
    if lic not in 허용라이선스:
        return False, f"라이선스 {lic or '미상'} -- 허용 목록 밖"
    if 항목["종류"] == "github-code":
        try:
            compile(항목["내용"], 항목.get("이름", "x.py"), "exec")
        except SyntaxError as e:
            return False, f"문법이 안 맞는다 ({e.lineno}행)"
        except (ValueError, TypeError) as e:
            return False, f"컴파일 불가 ({type(e).__name__})"
    return True, ""


def _해시(글: str) -> str:
    return hashlib.sha256(글.encode("utf-8", "replace")).hexdigest()[:12]


def 저장(항목: dict, 검색어: str, repo=None) -> str:
    """dig/corpus/<종류>-<해시>.md 로 적고 상대경로를 돌려준다."""
    repo = Path(repo or REPO)
    내용 = 항목["내용"][:파일글자]
    이름 = f"{항목['종류']}-{_해시(항목['url'] + 내용)}.md"
    p = repo / 말뭉치상대 / 이름
    p.parent.mkdir(parents=True, exist_ok=True)
    머리 = (f"---\n출처: {항목['url']}\n이름: {항목.get('이름', '')}\n종류: {항목['종류']}\n"
          f"라이선스: {항목.get('라이선스', '')}\n검색어: {검색어}\n"
          f"받은때: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"
          + (f"잘림: 원문 {len(항목['내용'])}자 중 {len(내용)}자\n" if len(항목["내용"]) > 파일글자 else "")
          + "---\n\n")
    p.write_text(머리 + 내용, encoding="utf-8")
    return f"{말뭉치상대}/{이름}"


def 색인(상대경로: str, 항목: dict, 검색어: str, repo=None) -> str:
    repo = Path(repo or REPO)
    본문 = (repo / 상대경로).read_text(encoding="utf-8", errors="replace")
    깃발 = night.깃발뽑기(Path(상대경로).name, f"{검색어} {항목.get('이름', '')}", 본문)
    깃발 = store.깃발정리(list(깃발) + re.findall(r"[0-9a-zA-Z가-힣_-]{2,}", 검색어) + [항목["종류"]])
    return store.적기(night.요약뽑기(항목["내용"], 500), 깃발, 상대경로, repo=repo, 지은이="코드")


# ---------------------------------------------------------------- 원장
def 원장읽기(repo=None) -> "list[dict]":
    p = Path(repo or REPO) / 원장상대
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _적기(repo, 줄: dict) -> None:
    p = Path(repo or REPO) / 원장상대
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


def 오늘받은수(repo=None) -> int:
    오늘 = time.strftime("%Y-%m-%d", time.gmtime())
    return sum(1 for r in 원장읽기(repo) if r.get("판정") == "색인" and str(r.get("때", "")).startswith(오늘))


# ---------------------------------------------------------------- 틈: 자가 틀린 자리
def 틈찾기(repo=None) -> "list[dict]":
    """eval 원장에서 참고를 줘도 틀린(마지막 판정) 과제 -> 그 깃발을 검색어로."""
    repo = Path(repo or REPO)
    from eval import tasks as T
    마지막: dict = {}
    for r in T.원장읽기(repo):
        if r.get("꼴") == "과제" and r.get("참고") == "있음":
            마지막[r["과제"]] = r
    과제들, _ = T.과제읽기(repo)
    깃 = {t["id"]: t for t in 과제들}
    out = []
    for pid, r in 마지막.items():
        if r.get("판정") != "틀림" or pid not in 깃:
            continue
        t = 깃[pid]
        말 = " ".join(t.get("깃발") or []) or t["물음"][:60]
        out.append({"과제": pid, "갈래": t["과제갈래"], "말": 말})
    return out


# ---------------------------------------------------------------- 한 바퀴
def 한바퀴(말들: "list[str]", repo=None, 몇: int = 5, 상한: int = 20,
        출처: "tuple[str, ...]" = 출처들) -> dict:
    repo = Path(repo or REPO)
    시작 = time.monotonic()
    결과 = {"돌았나": False, "받음": 0, "저장": 0, "색인": 0, "거절": [], "막힘": {}, "메모": "",
          "걸린초": 0.0, "적은것": []}
    말들 = [m.strip() for m in 말들 if m and m.strip()]
    if not 말들:
        결과["메모"] = "검색어가 없다 -- --말 을 주거나 자(eval/tasks)가 틀린 것이 있어야 한다"
        return 결과
    오늘 = 오늘받은수(repo)
    if 오늘 >= 하루상한():
        결과["메모"] = f"하루 상한 {하루상한()}개에 닿았다 (오늘 {오늘}개)"
        return 결과
    본것 = {(r.get("url"), r.get("해시")) for r in 원장읽기(repo)}
    한 = 한도()
    남은 = min(상한, 하루상한() - 오늘)
    for 말 in 말들:
        항목들: list[dict] = []
        if "github" in 출처 and 한.되나("github"):
            항목들 += 깃허브찾기(말, 몇, 한, repo)
        if "hf" in 출처 and 한.되나("hf"):
            항목들 += 허깅찾기(말, 몇, 한, repo)
        결과["받음"] += len(항목들)
        for it in 항목들:
            if 남은 <= 0:
                break
            해 = _해시(it["url"] + (it.get("내용") or "")[:파일글자])
            if (it["url"], 해) in 본것:
                continue
            본것.add((it["url"], 해))
            줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "종류": it["종류"],
                 "url": it["url"], "이름": it.get("이름", ""), "해시": 해,
                 "라이선스": it.get("라이선스", ""), "검색어": 말}
            돼, 까닭 = 검증(it)
            if not 돼:
                줄.update({"판정": "거절", "까닭": 까닭})
                결과["거절"].append(f"{it.get('이름', it['url'])[:50]}: {까닭}")
                _적기(repo, 줄)
                continue
            상대 = 저장(it, 말, repo)
            결과["저장"] += 1
            try:
                말씀 = 색인(상대, it, 말, repo)
            except ValueError as e:
                말씀 = f"색인 거절: {e}"
            if 말씀 == "적었다":
                결과["색인"] += 1
                남은 -= 1
            줄.update({"판정": "색인" if 말씀 == "적었다" else "저장만", "파일": 상대, "색인말": 말씀})
            결과["적은것"].append(상대)
            _적기(repo, 줄)
        if 남은 <= 0:
            결과["메모"] = f"상한 {상한}개에 닿아 멈췄다"
            break
    결과["막힘"] = dict(한.막힘)
    결과["걸린초"] = round(time.monotonic() - 시작, 1)
    # 첫 요청부터 다 막혔고 받은 것이 없으면 '돌았다' 고 하지 않는다.
    결과["돌았나"] = 결과["받음"] > 0 or not 결과["막힘"]
    return 결과


def 보고(결과: dict) -> str:
    줄 = []
    if not 결과["돌았나"]:
        줄.append("  못돌림 -- " + (결과.get("메모") or f"막힘 {결과.get('막힘')}"))
        return "\n".join(줄)
    줄.append(f"  받음 {결과['받음']} · 저장 {결과['저장']} · 색인 {결과['색인']} · 거절 {len(결과['거절'])}"
             f" · {결과['걸린초']}초")
    for x in 결과["거절"][:6]:
        줄.append(f"       거절 {x}")
    for 출, 까 in 결과["막힘"].items():
        줄.append(f"       막힘 {출}: {까} -- 이 바퀴는 여기까지")
    if 결과.get("메모"):
        줄.append(f"       {결과['메모']}")
    if 결과["색인"]:
        줄.append("  다음: `python3 eval/tasks.py --참고 둘다` 로 이 참고가 값을 하는지 재라")
    return "\n".join(줄)


def main() -> int:
    ap = argparse.ArgumentParser(description="밖에서 참고를 끌어와 검증·색인한다")
    ap.add_argument("--말", nargs="*", default=[], help="검색어 (여럿)")
    ap.add_argument("--틈", action="store_true", help="자(eval/tasks)가 틀린 과제의 깃발도 검색어로")
    ap.add_argument("--틈만", action="store_true", help="검색어만 보이고 안 받는다")
    ap.add_argument("--몇", type=int, default=5, help="출처·검색어마다 몇 개")
    ap.add_argument("--상한", type=int, default=20, help="이 바퀴에서 색인할 최대 수")
    ap.add_argument("--출처", default="github,hf")
    args = ap.parse_args()

    틈들 = 틈찾기() if (args.틈 or args.틈만) else []
    if args.틈만:
        for g in 틈들:
            print(f"  {g['갈래']:<3} {g['과제']:<22} -> {g['말']}")
        print(f"  틈 {len(틈들)}개" + ("" if 틈들 else " -- 자가 틀린 것이 없거나 아직 안 쟀다"))
        return 0 if 틈들 else 3
    말들 = list(args.말) + [g["말"] for g in 틈들]
    출처 = tuple(x.strip() for x in args.출처.split(",") if x.strip() in 출처들)
    결과 = 한바퀴(말들, 몇=args.몇, 상한=args.상한, 출처=출처)
    print(보고(결과))
    return 0 if 결과["돌았나"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
