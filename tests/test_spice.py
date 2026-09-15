"""`spice.py` -- 아날로그를 **실제로 돌린다.**

사용자(2026-09-15): "아날로그 회로도 바꾸고, 아날로그 회로 설계하고."

## 이 검사가 붙드는 것 -- **끝값 0 인 실패가 빨개지나**

실측 2026-09-15(ngspice 42). 세 가지가 **전부 끝값 0** 을 냈다.

    뜬 노드          Warning: singular matrix / gmin stepping failed   -> 끝값 0
    없는 노드 출력   vector nosuchnode is not available (아무 것도 안 찍힘) -> 끝값 0
    .meas 실패       meas ac nosuch ... failed!                        -> 끝값 0

`vvp` 가 FAIL 을 찍고도 0 을 내던 것과 같은 병이다. 끝값을 믿으면 깨진 회로가 전부
초록이다. 그래서 `spice.py` 는 **출력을 읽어 판정하고**, 이 검사는 그것이 실제로
빨개지는지를 본다. 다른 단언이 다 통과해도 이 셋이 안 빨개지면 이 장치는 쓸모가 없다.

## 그리고 숫자가 맞는지까지 본다

"PASS" 는 **쟀다**는 뜻이지 **맞다**는 뜻이 아니다. 실제로 이 파일을 지을 때
`meas ac fpeak WHEN vdb(b)=MAX` 가 2.25MHz 라는 엉뚱한 값을 내면서 PASS 로 찍혔다
(이론은 1.59MHz). 그래서 본보기마다 **제곱법칙 손계산과 대조한다** -- 넷리스트가
조용히 틀리면 그 대조가 빨개진다.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

뿌리 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(뿌리))
import spice                                                      # noqa: E402

FAIL = []


def ok(조건, 말):
    print(("  통과  " if 조건 else "  실패  ") + 말)
    if not 조건:
        FAIL.append(말)


# ---------------------------------------------------------------------------
# 1. 판정 -- 도구 없이도 늘 돈다. 이것이 안전망의 본체다.
# ---------------------------------------------------------------------------
print("\n[판정] 끝값 0 인 실패들")

거짓초록 = {
    "뜬 노드(singular matrix)":
        "Warning: singular matrix:  check node mid\nWarning: True gmin stepping failed\n"
        "\tout                              1.000000e+00\n",
    "DC 동작점 실패":
        "Warning: source stepping failed\n\tout   1.000000e+00\n",
    "없는 노드 출력":
        "Warning from checkvalid: vector nosuchnode is not available or has zero length.\n"
        "Doing analysis at TEMP = 27.000000\n",
    "분석 줄 없음":
        'Note: No ".plot", ".print", or ".fourier" lines; no simulations run\n',
    "넷리스트 오류":
        "Error on line 3 or its substitute:\n  q1 c b e mymodel\n"
        "could not find a valid modelname\n    Simulation interrupted due to error!\n",
    "수렴 실패":
        "Timestep too small; time = 1.0e-12\n\tout  1.000000e+00\n",
}
for 이름, 로그 in 거짓초록.items():
    판정, 왜, _ = spice.판정하기(로그)
    ok(판정 == spice.못잼, f"**{이름} -> 못잼** (PASS 로 읽히면 깨진 회로가 초록이다): {판정}")

판정, 왜, 잰것 = spice.판정하기(
    "vfin                =  9.932590e-01\n"
    " meas ac nosuch find v(out) at=1e30 failed!\n")
ok(판정 == spice.FAIL, f"**`.meas ... failed!` -> FAIL** (끝값은 0 이었다): {판정}")
ok(잰것.get("vfin") == 9.932590e-01, "실패한 판에서도 성공한 측정은 건져 온다")

판정, 왜, _ = spice.판정하기("Doing analysis at TEMP = 27.000000\nNote: Simulation executed\n")
ok(판정 == spice.못잼, f"**숫자가 하나도 안 찍히면 못잼** -- 돌긴 돌았다는 것은 통과가 아니다: {판정}")

판정, 왜, _ = spice.판정하기("\tout                              1.234500e+00\n")
ok(판정 == spice.못잼,
   f"**돌았는데 아무것도 안 쟀으면 못잼** -- 파형을 눈으로 보는 것은 검사가 아니다: {판정}")

# 뿌리 원인을 먼저 가리켜야 한다. "분석 줄이 없다" 로 읽히면 엉뚱한 데를 고치게 된다.
_, 왜, _ = spice.판정하기(
    "Error on line 9 or its substitute:\n  m1 d g 0 0 nch w=10u l=1u\n"
    "could not find a valid modelname\n"
    'Note: No ".plot", ".print", or ".fourier" lines; no simulations run\n')
ok("넷리스트" in 왜, f"**모델 오류가 '분석 줄 없음' 보다 먼저** 읽힌다: {왜[:40]}")

print("\n[판정] 확인 범위")
로그 = "av_db               =  1.355900e+01\nf3db                =  8.312500e+06\n"
ok(spice.판정하기(로그, "av_db 12 15")[0] == spice.PASS, "범위 안 -> PASS")
ok(spice.판정하기(로그, "av_db 20 25")[0] == spice.FAIL, "**범위 밖 -> FAIL**")
판정, 왜, _ = spice.판정하기(로그, "gm 1 2")
ok(판정 == spice.못잼, f"**안 잰 것을 확인하려 들면 못잼** -- 없는 것을 통과로 세지 않는다: {판정}")
ok(spice.판정하기(로그)[0] == spice.PASS, "`.meas` 만 있어도 PASS")

print("\n[판정] MAX 가 찍는 `at=` 자리도 잰 것이다")
잰것 = spice.잰것뽑기("vpk                 =  3.772531e+01 at=  1.584893e+06\n")
ok(잰것.get("vpk") == 37.72531, "값을 읽는다")
ok(잰것.get("vpk_at") == 1584893.0, "**`at=` 를 `vpk_at` 로 읽는다** -- 공진 주파수가 거기 있다")

print("\n[본보기] 여덟 개가 다 있고 이름 별칭이 돈다")
for 이름 in ("rc_lowpass", "mosfet_iv", "nmos_vth", "current_mirror",
            "common_source", "cmos_inverter_vtc", "diff_pair", "rlc_resonance"):
    ok(bool(spice.본보기찾기(이름)), f"본보기 {이름}")
    # **첫 줄은 제목으로 먹힌다.** 주석이 아니면 첫 카드가 통째로 사라진다(실측).
    ok(spice.본보기[이름].lstrip().startswith(("*", ".title")),
       f"{이름}: 첫 줄이 주석이다 (SPICE 가 제목으로 먹는다)")
ok(spice.본보기찾기("lambda") == spice.본보기["mosfet_iv"], "별칭 `lambda` -> mosfet_iv")
ok(spice.본보기찾기("Current Mirror") == spice.본보기["current_mirror"], "별칭이 대소문자·빈칸을 받는다")
ok(spice.본보기찾기("없는것") == "", "없는 이름은 빈 문자열")

# ---------------------------------------------------------------------------
# 2. 진짜로 돌린다. ngspice 가 없으면 여기만 건너뛴다.
# ---------------------------------------------------------------------------
if not spice.있나():
    print("\n[돌리기] ngspice 가 없다 -- 건너뛴다 (배포는 깐다)")
else:
    print("\n[돌리기] 손계산과 대조한다 -- PASS 는 '쟀다' 일 뿐이다")

    # 제곱법칙에서 손으로 뽑은 값. 넷리스트가 조용히 틀리면 여기가 빨개진다.
    Kp, λ = 200e-6, 0.05
    gm_cs = 2 * (Kp / 2 * 3 * 0.4 ** 2) / 0.4
    ro_cs = 1 / (λ * (Kp / 2 * 3 * 0.4 ** 2))
    Vov_dp = math.sqrt(2 * 50e-6 / (Kp * 20))
    손계산 = {
        "rc_lowpass":        ("f3db", 1 / (2 * math.pi * 1e3 * 1e-9), "1/(2πRC)"),
        "mosfet_iv":         ("lambda_est", λ / (1 + λ * 0.9), "모델의 LAMBDA 를 되찾는다"),
        "nmos_vth":          ("id_max", -(Kp / 2) * 10 * (1.79 - 0.5) ** 2 * (1 + λ * 1.8),
                              "(K'/2)(W/L)Vov²(1+λVds)"),
        "current_mirror":    ("iout_sat", 50e-6, "Iref 를 베낀다"),
        "common_source":     ("av_db",
                              20 * math.log10(gm_cs * (20e3 * ro_cs / (20e3 + ro_cs))),
                              "gm(RD‖ro)"),
        "cmos_inverter_vtc": ("vm", 0.9, "β 가 맞으면 VDD/2"),
        "diff_pair":         ("ad_db", 20 * math.log10((2 * 50e-6 / Vov_dp) * 20e3), "gm·RD"),
        "rlc_resonance":     ("vpk_at", 1 / (2 * math.pi * math.sqrt(100e-6 * 100e-12)),
                              "1/(2π√(LC))"),
    }
    for 이름, (칸, 참값, 근거) in 손계산.items():
        r = spice.돌리기(spice.본보기[이름], 초=180)
        ok(r["판정"] == spice.PASS, f"{이름}: {r['판정']} -- {r['왜']}")
        v = (r["잰것"] or {}).get(칸)
        if v is None:
            ok(False, f"{이름}: `{칸}` 을 못 쟀다 (잰 것: {list(r['잰것'] or {})})")
            continue
        차 = abs(v - 참값) / abs(참값) * 100
        ok(차 < 5, f"{이름}: {칸}={v:.5g} vs 손계산 {참값:.5g} ({차:.2f}%) -- {근거}")

    print("\n[돌리기] 일부러 틀린 것들이 실제로 빨개지나")

    뜬노드 = "* floating node\nV1 in 0 DC 1\nR1 in out 1k\nC1 out mid 1n\nR9 mid f2 1k\n.op\n"
    r = spice.돌리기(뜬노드, 초=60)
    ok(r["끝값"] == 0, f"(전제) ngspice 는 뜬 노드에 끝값 0 을 낸다: {r['끝값']}")
    ok(r["판정"] == spice.못잼, f"**뜬 노드가 빨개진다**: {r['판정']} -- {r['왜'][:50]}")

    없는노드 = ("* typo'd node name\nV1 in 0 DC 1\nR1 in 0 1k\n"
              ".control\nop\nprint v(nosuchnode)\n.endc\n")
    r = spice.돌리기(없는노드, 초=60)
    ok(r["끝값"] == 0, f"(전제) 없는 노드에도 끝값 0: {r['끝값']}")
    ok(r["판정"] == spice.못잼, f"**이름을 틀리면 빨개진다**: {r['판정']}")

    맞지만안잼 = ("* it runs and measures nothing\nV1 in 0 DC 1\nR1 in out 1k\nR2 out 0 1k\n"
                ".control\nop\nprint v(out)\n.endc\n")
    r = spice.돌리기(맞지만안잼, 초=60)
    ok(r["판정"] == spice.못잼,
       f"**멀쩡히 돌아도 안 쟀으면 못잼**: {r['판정']} -- {r['왜'][:40]}")

    r = spice.돌리기(spice.본보기["rc_lowpass"], "f3db 1.5e5 1.7e5", 초=90)
    ok(r["판정"] == spice.PASS, f"확인 범위 안: {r['판정']}")
    r = spice.돌리기(spice.본보기["rc_lowpass"], "f3db 1e6 2e6", 초=90)
    ok(r["판정"] == spice.FAIL, f"**확인 범위 밖이면 FAIL**: {r['판정']} -- {r['왜'][:60]}")

    r = spice.돌리기("", 초=10)
    ok(r["판정"] == spice.못잼, "빈 넷리스트 -> 못잼")

# ---------------------------------------------------------------------------
# 3. 배선 -- 봇이 실제로 쓸 수 있나, 배포가 깔아 주나
# ---------------------------------------------------------------------------
print("\n[배선]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
for 도구 in ("run_spice", "spice_example"):
    ok(f"def {도구}(" in 도구글, f"bot_tools 에 {도구}")
    ok(도구 in 서버.split("ADMIN_TOOLS = [")[1].split("]")[0], f"ADMIN_TOOLS 에 {도구}")
    ok(도구 in 공개.split("PUBLIC_TOOLS = [")[1].split("]")[0], f"PUBLIC_TOOLS 에 {도구}")
배포 = (뿌리 / ".github" / "workflows" / "deploy-oracle.yml").read_text(encoding="utf-8")
ok(" ngspice" in 배포, "**배포가 ngspice 를 깐다** -- 사람에게 시키지 않는다(G021)")
ok('- "spice.py"' in 배포, "spice.py 가 배포 트리거 paths 에 있다")

print()
if FAIL:
    print(f"실패 {len(FAIL)}개 -- {FAIL}")
    sys.exit(1)
print("spice: 끝값 0 인 실패가 빨개진다 · 숫자가 손계산과 맞는다 · 안 재면 못잼 -- 통과")
