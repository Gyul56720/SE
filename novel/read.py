"""지금까지 써진 것을 읽는다.

밤샘 런은 로그에 "몇 화 조립 시작" 만 찍는다. 그건 **구조가 섰다**는 뜻이지 산문이
채워졌다는 뜻이 아니다. 둘은 다른 단계이고, 읽을 수 있는 것은 후자뿐이다:

    조립(build_episode)  결말 하나 -> 회차들의 씬 배선. 아직 글자는 없다
    집필(drive/run_scene) 씬마다 대사·산문을 채우고 관문 20개를 통과시킨다

그래서 요약이 셋을 갈라 센다 -- 조립된 회차 / 산문이 있는 회차 / 검증까지 끝난 회차.
"검증까지 끝난" 것만 완성으로 세는 게 맞다. 나머지는 아직 고쳐 쓰는 중이다.

실행:
    python3 novel/read.py                      # 어디까지 왔는지 요약
    python3 novel/read.py --ep 3               # 3화 전문
    python3 novel/read.py --ep 1-10            # 1~10화
    python3 novel/read.py --ep 1-130 --out 원고.txt
    python3 novel/read.py --all --out 원고.txt  # 산문이 있는 것 전부
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 원고의 기본 위치는 **이 스크립트 옆**이다. 상대경로로 두면 ~/SE 밖에서
# 실행했을 때 "파일이 없다" 로 죽는다 -- 실제로 세 번 그랬다.
DEFAULT_PATH = Path(__file__).resolve().parent / "romance.json"

from novel.state import Novel                                         # noqa: E402


def parse_range(text: str) -> "list[int]":
    if "-" in text:
        lo, hi = text.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    return [int(text)]


def render_scenario(novel, episodes: "list[int]") -> str:
    """산문이 아직 없을 때 **디렉터가 쓴 시나리오**를 보여준다.

    조립은 끝났는데 집필이 못 간 회차라도 빈손이 아니다. direction["scenario"] 에 디렉터가
    쓴 Markdown 연출이 통째로 들어 있다 -- 공간·여는 사건·장치·화자의 시야·말하지 않는 것
    까지. 그것이 무엇이 만들어졌는지 눈으로 확인할 수 있는 유일한 것이고, 산문이 그 위에
    얹힐 재료다."""
    out = []
    for ep in episodes:
        scenes = sorted((s for s in novel.scenes if s.episode == ep), key=lambda s: s.id)
        if not scenes:
            continue
        out.append(f"\n\n{'=' * 60}\n{ep}화 시나리오 ({len(scenes)}씬)\n{'=' * 60}")
        for sc in scenes:
            d = sc.direction if isinstance(sc.direction, dict) else {}
            head = f"\n\n[{sc.id}]" + ("  (척추)" if sc.establishes else "  (서브플롯)")
            body = (d.get("scenario") or "").strip()
            if not body:
                # 시나리오 원문이 없으면 갖고 있는 조각이라도 보여준다
                order = [("staging", "공간"), ("trigger", "여는 사건"), ("props", "장치"),
                         ("camera", "화자의 시야"), ("subtext", "말하지 않는 것")]
                bits = [f"  {ko}: {d[k]}" for k, ko in order if d.get(k)]
                body = ((sc.directives[0] if sc.directives else "(비어 있다)")
                        + ("\n" + "\n".join(bits) if bits else ""))
            out.append(head + "\n" + body)
    return "".join(out)


def render(novel, episodes: "list[int]") -> str:
    out = []
    for ep in episodes:
        scenes = sorted((s for s in novel.scenes if s.episode == ep), key=lambda s: s.id)
        if not scenes:
            continue
        body = [s.prose.strip() for s in scenes if s.prose.strip()]
        if not body:
            continue
        chars = sum(len(b) for b in body)
        marks = {s.status for s in scenes}
        flag = "" if marks == {"verified"} else f"  [{'/'.join(sorted(marks))}]"
        out.append(f"\n\n{'=' * 60}\n{ep}화  ({chars:,}자){flag}\n{'=' * 60}\n")
        out.append("\n\n".join(body))
        end = next((s for s in scenes if s.is_episode_end and s.cliffhanger), None)
        if end:
            out.append(f"\n\n        -- 다음 화에 계속 ({end.cliffhanger}) --")
    return "".join(out)


def summarize(novel) -> str:
    from novel import arc
    eps = sorted({s.episode for s in novel.scenes if s.episode})
    built, written, done = [], [], []
    for ep in eps:
        scenes = [s for s in novel.scenes if s.episode == ep]
        built.append(ep)
        if any(s.prose.strip() for s in scenes):
            written.append(ep)
        if scenes and all(s.status == "verified" for s in scenes):
            done.append(ep)
    total = sum(len(s.prose) for s in novel.scenes)
    goal = 200 * arc.CHARS_PER_EPISODE

    def span(xs):
        return f"{xs[0]}~{xs[-1]}화 ({len(xs)}편)" if xs else "없음"

    lines = [
        f"제목        {novel.title}",
        f"목표        200화 · 회차당 {arc.CHARS_PER_EPISODE:,}자 = {goal:,}자",
        "",
        f"조립됨      {span(built)}   구조만 섰다. 아직 글자가 없을 수 있다",
        f"산문 있음   {span(written)}   읽을 수 있는 것은 여기까지다",
        f"검증 완료   {span(done)}   관문 20개를 통과했다",
        "",
        f"쓴 글자     {total:,}자 / {goal:,}자 ({total / goal:.1%})",
        f"씬          {len(novel.scenes)}개 "
        f"(verified {sum(1 for s in novel.scenes if s.status == 'verified')} · "
        f"pending {sum(1 for s in novel.scenes if s.status == 'pending')})",
    ]
    if written:
        avg = total / len(written)
        lines.append(f"회차 평균   {avg:,.0f}자 (목표 {arc.CHARS_PER_EPISODE:,})")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(DEFAULT_PATH))
    ap.add_argument("--ep", help="3 또는 1-10")
    ap.add_argument("--all", action="store_true", help="산문이 있는 회차 전부")
    ap.add_argument("--scenario", action="store_true",
                    help="산문 대신 디렉터 시나리오를 본다 (아직 집필 전인 회차용)")
    ap.add_argument("--out", help="파일로 저장 (없으면 화면)")
    a = ap.parse_args()

    path = Path(a.path)
    if not path.exists():
        print(f"{path} 가 없다. --path 로 원고 경로를 준다.")
        return 1
    novel = Novel.load(path)

    if not a.ep and not a.all:
        print(summarize(novel))
        print("\n읽으려면:  python3 novel/read.py --ep 1-10")
        return 0

    if a.scenario:
        episodes = (sorted({s.episode for s in novel.scenes if s.episode})
                    if a.all else parse_range(a.ep))
        text = render_scenario(novel, episodes)
    else:
        episodes = (sorted({s.episode for s in novel.scenes
                            if s.episode and s.prose.strip()})
                    if a.all else parse_range(a.ep))
        text = render(novel, episodes)
    if not text.strip():
        print(f"{a.ep or '전체'} 구간에 아직 산문이 없다. 조립만 된 상태다.")
        print("디렉터가 쓴 시나리오는 남아 있다:  "
              f"python3 novel/read.py --scenario --ep {a.ep or '1-10'}")
        return 1
    if a.out:
        Path(a.out).write_text(text.lstrip(), encoding="utf-8")
        print(f"{a.out} 에 {len(text):,}자 저장했다.")
    else:
        print(text.lstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
