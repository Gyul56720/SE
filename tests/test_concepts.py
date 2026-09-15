"""`concepts.py` -- 집적회로 개념 목록. **적혀 있다고 덮인 것이 아니다.**

사용자(2026-09-15): "current mirror 말고도 학부 석사 박사 아날로그 집적회로,
디지털 집적 회로에 쓰이는 개념들을 모두 cover 할 수 있어야 해."

## 이 검사가 붙드는 것 -- 목록이 거짓말을 못 하게

개념 이름 백 개를 프롬프트에 적는 것은 coverage 가 아니다. 그것은 이 저장소가 내내
말해 온 "검사하지 않은 초록" 이다 -- 적혀 있으니 된 줄 알지만 아무도 확인 안 했다.

그래서 목록을 데이터로 두고 **여기서 전부 두들긴다.**

    1. `넷리스트` 가 가리키는 본보기를 **실제로 돌린다** (없거나 안 돌면 빨강)
    2. `회로도` 가 가리키는 본보기를 **실제로 그린다**
    3. 식 95개를 **실제로 그려 본다** -- 안 그려지면 빨강
    4. 끊긴 `이웃` 링크, 끊긴 별칭, 겹친 이름

## 식이 그려지는지는 예외로 알 수 없다 -- 실측 2026-09-15

`\\text{정합}` 처럼 한글이 든 식을 mathtext 에 넣으면 **예외가 안 난다.**
글리프가 없으면 두부(□)로 바꿔 그리고 **경고만** 낸다. 그래서 `try/except` 로 재면
95개 전부 초록이 나온다 -- 그런데 다섯 개가 두부였다.

그리고 그 경고는 `warnings` 가 아니라 **`logging`** 으로 나온다. `catch_warnings` 로
잡으려 했더니 또 0 이 나왔다. **두 번 연달아 거짓 초록이었다.** 그래서 여기서는
matplotlib 로거에 손을 달아 `does not have a glyph` 를 센다.

회로도에서 한글 라벨이 두부로 그려지면서 성공을 반환하던 것과 같은 병이다.
"""
from __future__ import annotations

import collections
import io
import logging
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import concepts as k                                              # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


이름들 = {c["이름"] for c in k.개념}

print("\n[목록] 짜임새")
ok(len(k.개념) >= 80, f"개념이 충분히 있다: {len(k.개념)}개")
겹 = [n for n, v in collections.Counter(c["이름"] for c in k.개념).items() if v > 1]
ok(not 겹, f"이름이 안 겹친다: {겹}")
for 칸 in ("이름", "한글", "층", "갈래", "식", "말"):
    빈것 = [c["이름"] for c in k.개념 if not c[칸]]
    ok(not 빈것, f"`{칸}` 이 빈 항목이 없다: {빈것[:3]}")
ok(all(c["층"] in (k.학부, k.석사, k.박사) for c in k.개념), "층이 셋 중 하나다")
ok(all(c["갈래"] in (k.A, k.D, k.DEV, k.M) for c in k.개념), "갈래가 넷 중 하나다")
셈 = k.덮임()
for 층 in (k.학부, k.석사, k.박사):
    ok(셈["층별"][층] >= 8, f"{층} 개념이 {셈['층별'][층]}개")
for g in (k.A, k.D):
    ok(셈["갈래별"][g] >= 25, f"{g} 개념이 {셈['갈래별'][g]}개")

print("\n[링크] 끊긴 데가 없다")
끊긴이웃 = [(c["이름"], n) for c in k.개념 for n in c["이웃"] if n not in 이름들]
ok(not 끊긴이웃, f"**`이웃` 이 다 실제 개념을 가리킨다**: {끊긴이웃[:4]}")
끊긴별칭 = {a: t for a, t in k.별칭.items() if t not in 이름들}
ok(not 끊긴별칭, f"**별칭이 다 실제 개념을 가리킨다**: {끊긴별칭}")

print("\n[찾기] 사용자가 쓰는 말로 찾힌다")
물음 = [("cascode", "Cascode"), ("밀러", "Miller effect"), ("gm/ID", "gm/ID methodology"),
       ("SNM", "SRAM read/write margin"), ("pll", "PLL basics"), ("FO4", "Fanout of 4"),
       ("채널길이변조", "Channel-length modulation"), ("setup", "Setup and hold"),
       ("kT/C", "kT/C noise"), ("current_mirror", "Current mirror"), ("CDC", "CDC and synchronizers"),
       ("몸효과", "Body effect"), ("slew rate", "Slew rate"), ("누설", "Leakage power")]
for q, 바람 in 물음:
    난것 = k.찾기(q, 3)
    ok(any(c["이름"] == 바람 for c in 난것),
       f"`{q}` -> {바람} ({[c['이름'] for c in 난것[:2]]})")
# **별칭을 하나씩 다 두들긴다.** 손으로 고른 물음 열넷만 보면 별칭 하나를 지워도
# 아무 검사도 안 빨개진다(실측 2026-09-15: 그 변형이 살아남아 미해결로 남았다).
# 살아남은 변형은 "같다" 가 아니라 "아직 반례를 못 썼다" 는 뜻이다 -- 그래서 여기 쓴다.
# 그런데 **`k.별칭` 을 돌면서 검사하면 지운 별칭은 애초에 안 돌아본다.** 검사 대상에서
# 기대값을 뽑으면 삭제를 영영 못 잡는다(실측: 위 전수 검사를 붙이고도 그 변형이 살았다).
# 그래서 있어야 하는 것들을 **여기 바깥에 못 박는다** -- 사용자가 실제로 칠 말들이다.
필수별칭 = {
    "clm": "Channel-length modulation", "vth": "Threshold voltage",
    "gm": "Transconductance", "ro": "Output resistance",
    "vov": "Overdrive voltage", "cs": "Common source", "cg": "Common gate",
    "sf": "Source follower", "mirror": "Current mirror", "miller": "Miller effect",
    "ota": "Two-stage Miller OTA", "opamp": "Two-stage Miller OTA",
    "gbw": "Gain-bandwidth product", "sr": "Slew rate", "ktc": "kT/C noise",
    "1/f": "Flicker noise", "pelgrom": "Mismatch (Pelgrom)", "mc": "Monte Carlo",
    "sar": "SAR ADC", "enob": "SNDR / ENOB", "pll": "PLL basics",
    "vco": "VCO phase noise", "vtc": "CMOS inverter VTC", "le": "Logical effort",
    "fo4": "Fanout of 4", "tg": "Transmission gate", "setup": "Setup and hold",
    "sta": "Static timing analysis", "cdc": "CDC and synchronizers",
    "sram": "SRAM 6T cell", "snm": "SRAM read/write margin",
    "elmore": "Interconnect RC delay", "gm/id": "gm/ID methodology",
}
없어진 = sorted(a for a in 필수별칭 if a not in k.별칭)
ok(not 없어진, f"**있어야 할 별칭이 다 있다** (지우면 여기가 빨개진다): {없어진}")
틀린 = [(a, t, k.별칭.get(a)) for a, t in 필수별칭.items() if k.별칭.get(a) not in (None, t)]
ok(not 틀린, f"필수 별칭이 제 개념을 가리킨다: {틀린[:4]}")

안맞는별칭 = []
for _a, _t in k.별칭.items():
    _r = k.찾기(_a, 1)
    if not _r or _r[0]["이름"] != _t:
        안맞는별칭.append((_a, _t, _r[0]["이름"] if _r else None))
ok(not 안맞는별칭,
   f"**별칭 {len(k.별칭)}개가 다 제 개념을 1등으로 낸다**: {안맞는별칭[:4]}")

ok(k.찾기("") == [], "빈 물음은 빈 답")
ok(k.찾기("zzzznotaconcept") == [], "없는 것은 빈 답 -- 아무거나 주지 않는다")

print("\n[식] **그려지나** -- 예외가 아니라 두부를 본다")
import matplotlib                                                  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
import latex_formatter as L                                        # noqa: E402
L.글꼴세우기()
버퍼 = io.StringIO()
손 = logging.StreamHandler(버퍼)
_lg = logging.getLogger("matplotlib")
_lg.addHandler(손)
_lg.setLevel(logging.WARNING)


def _그려보기(식: str) -> "tuple[bool, str]":
    """(그려졌나, 까닭). **두부는 그려진 것으로 안 센다.**"""
    버퍼.truncate(0)
    버퍼.seek(0)
    try:
        fig = plt.figure(figsize=(6, 1))
        fig.text(0.01, 0.5, f"${L.손질(식)}$", fontsize=13)
        fig.canvas.draw()
        plt.close(fig)
    except Exception as e:                                          # noqa: BLE001
        plt.close("all")
        return False, f"{type(e).__name__}: {e}"
    if "does not have a glyph" in 버퍼.getvalue():
        return False, "글리프가 없어 **두부(□)로 그려진다**"
    return True, ""


# 먼저 이 장치가 진짜로 가르는지 본다. 늘 초록인 검사는 없느니만 못하다.
ok(_그려보기(r"V_{th}=V_{th0}+\gamma\sqrt{V_{SB}}")[0], "(장치 점검) 멀쩡한 식은 그려진다")
ok(not _그려보기(r"A_v=\text{이득}")[0],
   "**(장치 점검) 한글이 든 식은 두부로 잡힌다** -- 이게 안 잡히면 아래가 다 허수다")
ok(not _그려보기(r"\frac{1}{")[0], "(장치 점검) 깨진 LaTeX 는 터진다")

못그림 = []
for c in k.개념:
    됐나, 왜 = _그려보기(c["식"])
    if not 됐나:
        못그림.append((c["이름"], 왜))
ok(not 못그림, f"**식 {len(k.개념)}개가 다 그려진다**: {못그림[:4]}")
한글식 = [c["이름"] for c in k.개념 if re.search(r"[가-힣]", c["식"])]
ok(not 한글식, f"**식에 한글이 없다** -- 있으면 두부가 된다: {한글식}")
ok(not [c["이름"] for c in k.개념 if "$" in c["식"]],
   "식에 `$` 가 없다 -- 부르는 쪽이 감싼다")
불균형 = [c["이름"] for c in k.개념 if c["식"].count("{") != c["식"].count("}")]
ok(not 불균형, f"중괄호가 맞는다: {불균형}")

print("\n[본보기] 가리키는 데가 **실제로 돌아간다**")
import spice                                                       # noqa: E402
import circuitdraw                                                 # noqa: E402

넷들 = sorted({c["넷리스트"] for c in k.개념 if c["넷리스트"]})
그림들 = sorted({c["회로도"] for c in k.개념 if c["회로도"]})
ok(len(넷들) >= 6, f"넷리스트를 가리키는 개념이 있다: {len(넷들)}가지")
ok(len(그림들) >= 5, f"회로도를 가리키는 개념이 있다: {len(그림들)}가지")
# **가리키는 데가 있다고 맞는 것이 아니다.** 실측 2026-09-15: 일괄 편집이 `Slew rate` 에
# `twostage_ota` 를, `Static CMOS logic` 에 `noise_margins` 를 붙였다. 둘 다 실재하는
# 본보기라 "없는 것을 가리키나" 검사는 조용히 통과했다 -- 엉뚱한 데를 가리켰을 뿐이다.
# 그래서 중요한 짝은 **여기 바깥에 못 박는다**(별칭 때와 같은 처방).
필수연결 = {
    "Current mirror": "current_mirror", "Cascode": "cascode",
    "Cascode current mirror": "cascode_mirror", "Source follower": "source_follower",
    "Common gate": "common_gate", "Common source": "common_source",
    "Miller effect": "miller", "Body effect": "body_effect",
    "gm/ID methodology": "gm_id", "CMRR": "cmrr",
    "Differential pair": "diff_pair", "Two-stage Miller OTA": "twostage_ota",
    "Slew rate": "slew_rate", "Flicker noise": "flicker_noise",
    "Distortion HD2/HD3/IIP3": "distortion", "Monte Carlo": "mc_mirror",
    "Mismatch (Pelgrom)": "mc_mirror", "kT/C noise": "rc_noise",
    "CMOS inverter VTC": "cmos_inverter_vtc", "Noise margins": "noise_margins",
    "Static CMOS logic": "nand_stack", "Propagation delay": "inverter_delay",
    "Dynamic power": "inverter_power", "Transmission gate": "transmission_gate",
    "Dynamic / domino logic": "charge_sharing", "SRAM 6T cell": "sram_read_disturb",
    "Interconnect RC delay": "elmore", "Channel-length modulation": "mosfet_iv",
    "Threshold voltage": "nmos_vth", "RLC resonance and Q": "rlc_resonance",
    "RC low-pass / first-order response": "rc_lowpass",
}
_어디 = {c["이름"]: c for c in k.개념}
어긋난것 = []
for 이름, 넷 in 필수연결.items():
    c = _어디.get(이름)
    if c is None:
        어긋난것.append((이름, "그런 개념이 없다"))
    elif c["넷리스트"] != 넷:
        어긋난것.append((이름, f"{c['넷리스트']!r} 인데 {넷!r} 이어야 한다"))
ok(not 어긋난것,
   f"**핵심 개념 {len(필수연결)}개가 제 본보기를 가리킨다** (엉뚱한 데를 가리켜도 "
   f"'없는 것' 검사는 통과한다): {어긋난것[:4]}")

없는넷 = [(c["이름"], c["넷리스트"]) for c in k.개념
        if c["넷리스트"] and c["넷리스트"] not in spice.본보기]
ok(not 없는넷, f"**없는 넷리스트를 가리키지 않는다**: {없는넷}")
없는그림 = [(c["이름"], c["회로도"]) for c in k.개념
         if c["회로도"] and c["회로도"] not in circuitdraw.본보기]
ok(not 없는그림, f"**없는 회로도를 가리키지 않는다**: {없는그림}")

if not spice.있나():
    print("  ngspice 가 없다 -- 돌리기는 건너뛴다 (배포는 깐다)")
else:
    for 이름 in 넷들:
        r = spice.돌리기(spice.본보기[이름], 초=120)
        ok(r["판정"] == spice.PASS,
           f"**`{이름}` 이 실제로 돈다**: {r['판정']} -- {r['왜'][:60]}")

판 = tempfile.mkdtemp(prefix="conc-")
for 이름 in 그림들:
    쪽 = os.path.join(판, f"{abs(hash(이름))}.png")
    r = circuitdraw.본보기그리기(이름, 쪽)
    됐 = r.get("됐나") and os.path.exists(쪽) and os.path.getsize(쪽) > 1000
    ok(bool(됐), f"**`{이름}` 이 실제로 그려진다**: {r.get('왜', '')[:60]}")
shutil.rmtree(판, ignore_errors=True)

print("\n[말로] 사람이 읽는 꼴")
c = k.찾기("cascode")[0]
글 = k.말로(c)
ok(c["이름"] in 글 and c["한글"] in 글, "이름과 한글이 들어간다")
ok("$$" in 글, "식을 `$$` 로 감싼다 -- 봇이 그림으로 바꾼다")
c2 = k.찾기("current mirror")[0]
ok("run_spice" in k.말로(c2) and "draw_circuit" in k.말로(c2),
   "**본보기가 있으면 부르는 법을 같이 준다** -- 설명만 하고 끝내지 않게")
ok("run_spice" not in k.말로(k.찾기("CMFB")[0]),
   "본보기가 없으면 있는 척하지 않는다")

print("\n[덮임] 몇 개가 진짜로 돌아가는지 **센다**")
ok(셈["돌려볼수있음"] + 셈["설명만"] == 셈["모두"], f"셈이 맞는다: {셈}")
ok(셈["돌려볼수있음"] >= 15,
   f"**적어도 15개는 돌려볼 수 있다** (지금 {셈['돌려볼수있음']}개)")
ok(셈["설명만"] > 0, "설명뿐인 것을 0 으로 꾸미지 않는다")

print("\n[배선]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
ok("def concept(" in 도구글, "bot_tools 에 concept")
ok("concept" in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0], "ADMIN_TOOLS 에")
ok("concept" in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0], "PUBLIC_TOOLS 에")
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok('- "concepts.py"' in 배포, "concepts.py 가 배포 트리거 paths 에 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL[:6]}")
    sys.exit(1)
print(f"concepts: {len(k.개념)}개 · 식이 다 그려진다 · 가리키는 본보기가 다 돈다 -- 통과")
