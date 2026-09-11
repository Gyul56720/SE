"""모델 요약 검증(verify)과 다섯 꼴 간선(link) · 요지문 승격/강등(digest)을 임시
저장소에서 **실제로 돌려** 붙든다.

붙드는 것: (1) 대조 꼴이 지어낸 수·깃발·헛말을 어긋남으로 잡고 성한 요약은 통과시킨다,
(2) 밤일에서 모델 제안은 대조를 통과해야만 채택되고 퇴짜면 코드 요약으로 물러선다,
(3) 네 꼴(대조·재계산·기준선·뒤집기)이 코드로 판정되고 연역은 관할 밖이라 말한다,
(4) 간선은 append-only 로 쌓이되 같은 판정은 다시 안 적는다, (5) 요지문은 어긋난
기억을 강등하고 검증된 이례만 승격한다 -- '읽힐 텍스트' 는 판정이 정한다.

LLM·네트워크 없이 돈다(요약기는 가짜). 실행: python3 tests/test_graph_판정.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))

from graph import digest, link, night, store, verify  # noqa: E402

FAIL = []


def ok(cond, what):
    print(("  통과  " if cond else "  실패  ") + what)
    if not cond:
        FAIL.append(what)


원문 = ("# 촉매 실험\n\n백금 촉매 온도 350도에서 수율 82%. 니켈은 61%에 그쳤다. "
       "촉매 갈래 중 백금이 제일 낫다.\n")

print("== 대조 꼴: 요약이 원문에 서 있는가 ==")
r = verify.대조("백금 촉매가 350도에서 수율 82%로 니켈(61%)을 이겼다",
               ["촉매", "백금", "202609"], 원문, 이름="촉매_실험.md")
ok(r["판정"] == "맞음", f"성한 요약은 맞음 ({r})")
r = verify.대조("백금 촉매 수율 99%", ["촉매"], 원문)
ok(r["판정"] == "어긋남" and any("없는 수" in v for v in r["위반"]),
   f"**지어낸 수(99)를 잡는다** ({r['위반']})")
r = verify.대조("백금 촉매 수율 82%", ["촉매", "양자컴퓨터"], 원문)
ok(r["판정"] == "어긋남" and any("없는 깃발" in v for v in r["위반"]),
   f"지어낸 깃발을 잡는다 ({r['위반']})")
r = verify.대조("우주 정거장에서 감자 농사가 대풍년이었다", ["촉매"], 원문)
ok(r["판정"] == "어긋남" and any("근거율" in v for v in r["위반"]),
   f"원문에 없는 말투성이 요약을 잡는다 ({r['위반']})")
ok(verify.대조("", [], "")["판정"] == "미검증", "잴 것이 없으면 미검증 -- 참/거짓 둘뿐인 꼴은 없다")

임시 = Path(tempfile.mkdtemp(prefix="test-graph-판정-"))
repo = 임시 / "repo"
(repo / "public_agent_memory").mkdir(parents=True)
노트 = repo / "public_agent_memory" / "20260901-120000_촉매_실험_기록.md"
노트.write_text(f"---\ntopic: '촉매 실험'\n---\n\n{원문}", encoding="utf-8")

try:
    print("\n== 밤일: 모델 제안은 대조를 통과해야만 채택된다 ==")

    def 성한요약기(이름, topic, body):
        return {"요약": "백금 촉매 350도 수율 82%, 니켈 61% -- 백금이 낫다",
                "깃발": ["백금", "니켈"]}

    r = night.간추리기(repo=repo, 요약기=성한요약기)
    ok(len(r["적음"]) == 1 and not r["퇴짜"], f"성한 제안은 채택 ({r['퇴짜']})")
    node = store.읽기(repo)[0][0]
    ok(node["지은이"] == "모델(대조통과)" and "니켈" in node["요약"],
       f"**지은이가 남는다** ({node['지은이']!r})")
    ok("백금" in node["깃발"], f"제안 깃발이 코드 깃발에 합쳐진다 ({node['깃발']})")

    def 지어내는요약기(이름, topic, body):
        return {"요약": "백금 촉매 수율 99.9%로 세계 신기록", "깃발": ["신기록"]}

    노트2 = repo / "public_agent_memory" / "20260902-010101_니켈_추가_실험.md"
    노트2.write_text("---\ntopic: '니켈 추가'\n---\n\n니켈 촉매 재실험, 수율 63%.\n",
                    encoding="utf-8")
    r = night.간추리기(repo=repo, 요약기=지어내는요약기)
    ok(len(r["퇴짜"]) == 1 and "어긋남" in r["퇴짜"][0],
       f"**지어낸 제안은 퇴짜** ({r['퇴짜']})")
    node2 = [n for n in store.읽기(repo)[0] if "니켈_추가" in n["출처"]][0]
    ok(node2["지은이"] == "코드" and "63" in node2["요약"],
       "퇴짜면 코드 요약으로 물러선다 -- 밤일은 멈추지 않는다")

    def 죽는요약기(이름, topic, body):
        raise RuntimeError("쿼터 소진")

    노트3 = repo / "public_agent_memory" / "20260903-010101_구리_실험.md"
    노트3.write_text("구리 촉매 수율 40%.\n", encoding="utf-8")
    r = night.간추리기(repo=repo, 요약기=죽는요약기)
    ok(len(r["적음"]) == 1 and "죽었다" in (r["퇴짜"] or [""])[0],
       f"요약기가 죽어도 밤일은 계속된다 ({r['퇴짜']})")

    print("\n== 다섯 꼴 간선: 네 꼴은 코드가, 연역은 관할 밖 ==")
    간선들, 관할밖 = link.판정들(node, repo=repo)
    꼴별 = {e["꼴"]: e for e in 간선들}
    ok(set(꼴별) == {"대조", "재계산", "기준선", "뒤집기"}, f"네 꼴이 다 있다 ({set(꼴별)})")
    ok(꼴별["대조"]["판정"] == "맞음", f"대조: 채택된 요약이라 맞음 ({꼴별['대조']})")
    ok(꼴별["재계산"]["판정"] == "같음", "재계산: 해시·글자수가 같다")
    ok(꼴별["기준선"]["판정"] == "못잼" and "개뿐" in 꼴별["기준선"]["근거"],
       f"기준선: 원장이 작으면 **못잼이라 말한다** ({꼴별['기준선']['근거'][:40]})")
    ok("관할 밖" in 관할밖 and "reason" in 관할밖,
       "**연역은 관할 밖 -- reason/ 을 가리킨다.** 여기서 지어내지 않는다")

    적힘, _ = link.기록(node, repo=repo)
    ok(len(적힘) == 4, f"간선 4개가 적혔다 ({len(적힘)})")
    적힘2, 건너뜀2 = link.기록(node, repo=repo)
    ok(not 적힘2 and 건너뜀2 == 4, f"같은 판정은 다시 안 적는다 ({건너뜀2}건 건너뜀)")

    print("\n== 원본이 바뀌면 재계산이 '다름' 을 적는다 ==")
    노트.write_text(노트.read_text(encoding="utf-8") + "\n(덧붙임)\n", encoding="utf-8")
    적힘3, _ = link.기록(node, repo=repo)
    꼴별3 = {e["꼴"]: e for e in 적힘3}
    ok(꼴별3.get("재계산", {}).get("판정") == "다름", f"재계산=다름 ({꼴별3.get('재계산')})")
    ok(len(link.간선읽기(repo)) > 4, "어긋난 판정도 지우지 않고 쌓인다 (append-only)")

    print("\n== 요지문: 판정이 승격과 강등을 정한다 ==")
    for n in [node2]:
        link.기록(n, repo=repo)
    글 = digest.짓기(repo=repo)
    ok("손으로 고치지 마라" in 글, "파생 문서라고 머리에 적는다 -- 두 진실을 안 둔다")
    ok("경고" in 글 and node["출처"] in 글,
       "**갈라진 기억(재계산=다름)은 경고 절로 강등된다**")
    경고앞 = 글.split("## 깃발 지도")[0]
    본문승격 = 글.split("## 경고")[-1].split("##", 1)[-1] if "## 경고" in 글 else 글
    ok(node["요약"][:20] not in 본문승격 or node["출처"] in 경고앞,
       "강등된 기억의 요약은 본문에 안 올라간다")
    digest.쓰기(repo=repo)
    ok((repo / "graph" / "digest.md").is_file(), "digest.md 가 실제로 지어진다")

    print("\n== 기준선: 원장이 차면 이례/평범을 가른다 ==")
    for i in range(12):
        p = repo / "public_agent_memory" / f"2026090{i % 9 + 1}-11{i:02d}00_배송_지연_{i}.md"
        p.write_text(f"배송 지연율 {i}% 기록. 배송 원장 대조.\n", encoding="utf-8")
    night.간추리기(repo=repo)
    nodes = {n["출처"]: n for n in store.읽기(repo)[0]}
    배송 = [n for 출처, n in nodes.items() if "배송" in 출처][0]
    간선들, _ = link.판정들(배송, repo=repo)
    기준선 = {e["꼴"]: e for e in 간선들}["기준선"]
    ok(기준선["판정"] == "평범", f"흔한 깃발(배송)은 평범 ({기준선['근거'][:40]})")
    구리 = [n for 출처, n in nodes.items() if "구리" in 출처][0]
    간선들, _ = link.판정들(구리, repo=repo)
    기준선 = {e["꼴"]: e for e in 간선들}["기준선"]
    ok(기준선["판정"] == "이례", f"저만의 깃발(구리)은 이례 ({기준선['근거'][:50]})")
finally:
    shutil.rmtree(임시, ignore_errors=True)

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    raise SystemExit(1)
print("판정: 대조 잡음 · 모델 퇴짜/채택 · 네 꼴 판정 · 연역 관할밖 · 요지 승격/강등 -- 통과")
