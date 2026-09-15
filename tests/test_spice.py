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
import re
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
            "common_source", "cmos_inverter_vtc", "diff_pair", "rlc_resonance",
            "mc_mirror", "rc_noise"):
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

    print("\n[돌리기] 2차 본보기도 손계산과 대조한다")

    def 잰다(이름, 초=200):
        r = spice.돌리기(spice.본보기[이름], 초=초)
        ok(r["판정"] == spice.PASS, f"{이름}: {r['판정']} -- {r['왜'][:50]}")
        return r["잰것"] or {}, r["로그"] or ""

    def 가깝나(이름, 잰값, 참값, 안에, 근거):
        차 = abs(잰값 - 참값) / abs(참값) * 100
        ok(차 < 안에, f"{이름}: {잰값:.5g} vs 손계산 {참값:.5g} ({차:.1f}%) -- {근거}")

    def 로그값(로그, 이름):
        m = re.search(rf"^\s*{re.escape(이름)}\s*=\s*([-+0-9.eE]+)", 로그, re.M)
        return float(m.group(1)) if m else None

    # --- gm/ID: 제곱법칙이 그대로 나온다. 가장 날카로운 대조다.
    잰것, _ = 잰다("gm_id")
    for 칸, vov in (("gmid_vov100m", 0.1), ("gmid_vov400m", 0.4), ("gmid_vov800m", 0.8)):
        가깝나("gm_id/" + 칸, 잰것[칸], 2 / vov, 2, f"gm/ID = 2/Vov (Vov={vov})")
    가깝나("gm_id/gain", 잰것["gain_vov800m"], 2 / (0.05 * 0.8), 10, "gm/gds = 2/(lambda*Vov)")

    # --- 몸효과: GAMMA*(sqrt(PHI+Vsb)-sqrt(PHI)). **SPICE 의 PHI 가 2*phi_F 다.**
    잰것, _ = 잰다("body_effect")
    가깝나("body_effect", 잰것["dvth"], 0.4 * (math.sqrt(0.7 + 0.5) - math.sqrt(0.7)), 5,
          "dVth = GAMMA(sqrt(PHI+Vsb)-sqrt(PHI))")

    # --- 밀러: Cin = Cgs + Cgd(1+|Av|). 모델의 CGSO·CGDO 에서 곧바로 나온다.
    잰것, 로그 = 잰다("miller")
    cgd = 0.3e-9 * 30e-6
    ok(abs(잰것["cin_flat"] - 2 * cgd) / (2 * cgd) < 0.05,
       f"이득 없을 때 Cin = Cgs+Cgd = {2*cgd:.4g}: {잰것['cin_flat']:.4g}")
    av = 10 ** (잰것["av_db"] / 20)
    가깝나("miller/Cin", 잰것["cin_gain"], cgd * (2 + av), 10,
          f"Cgs + Cgd(1+|Av|), |Av|={av:.2f}")
    ok(잰것["miller_ratio"] > 4,
       f"**이득이 있으면 입력 용량이 몇 배로 는다**: {잰것['miller_ratio']:.2f}배")

    # --- 소스팔로워·공통게이트: AC 이득이 소신호식과 맞나(동작점의 gm 을 써서 대조)
    잰것, 로그 = 잰다("source_follower")
    gm, gmb, gds = (로그값(로그, x) for x in ("@m1[gm]", "@m1[gmbs]", "@m1[gds]"))
    가깝나("source_follower", 10 ** (잰것["av_db"] / 20), gm / (gm + gmb + gds), 2,
          "Av = gm/(gm+gmb+gds) < 1")
    ok(잰것["av_db"] < 0, f"**이득이 1 을 못 넘는다**: {잰것['av_db']:.3f} dB")

    잰것, 로그 = 잰다("common_gate")
    gm, gmb, gds = (로그값(로그, x) for x in ("@m1[gm]", "@m1[gmbs]", "@m1[gds]"))
    가깝나("common_gate", 10 ** (잰것["av_db"] / 20), (gm + gmb) * (20e3 * (1 / gds) / (20e3 + 1 / gds)),
          5, "Av = (gm+gmb)(RD||ro), 반전이 아니다")

    # --- 캐스코드: Rout 이 ro 의 gm*ro 배로 뛴다
    잰것, 로그 = 잰다("cascode")
    gm2, gds1 = 로그값(로그, "@m2[gm]"), 로그값(로그, "@m1[gds]")
    rout = abs(로그값(로그, "rout"))
    ok(rout > 20e6, f"Rout 이 수십 메그옴이다: {rout:.3g}")
    가깝나("cascode/Rout", rout, gm2 / (gds1 ** 2), 40, "Rout ~ gm2*ro2*ro1")
    ok(rout / (1 / gds1) > 50,
       f"**단일 소자 ro 의 {rout/(1/gds1):.0f}배** -- 그것이 캐스코드의 전부다")

    잰것, 로그 = 잰다("cascode_mirror")
    가깝나("cascode_mirror/I", abs(잰것["i_lo"]), 50e-6, 5, "Iref 를 베낀다")
    ok(abs(잰것["i_hi"] - 잰것["i_lo"]) / abs(잰것["i_lo"]) < 0.005,
       f"**출력 전압이 0.6V 움직여도 전류가 안 변한다**: "
       f"{abs(잰것['i_hi']-잰것['i_lo'])/abs(잰것['i_lo'])*100:.3f}%")

    # --- CMRR: 꼬리 전류원의 ro 가 정한다
    잰것, 로그 = 잰다("cmrr")
    cmrr = 잰것["ad_db"] - 잰것["acm_db"]
    gm1, gds3 = 로그값(로그, "@m1[gm]"), 로그값(로그, "@m3[gds]")
    가깝나("cmrr", cmrr, 20 * math.log10(2 * gm1 / gds3), 15, "CMRR ~ 2*gm*r_tail")
    ok(잰것["acm_db"] < 0, f"공통모드는 깎인다: {잰것['acm_db']:.2f} dB")

    # --- 디지털
    잰것, _ = 잰다("inverter_delay")
    t10, t40 = 잰것["tphl_10f"], 잰것["tphl_40f"]
    ok(t40 > t10, f"부하가 늘면 느려진다: {t10*1e12:.1f}ps -> {t40*1e12:.1f}ps")
    ok(1.5 < t40 / t10 < 3.5,
       f"**부하 4배에 지연은 4배가 아니다** -- 자기부하(절편)가 있다: {t40/t10:.2f}배")

    잰것, 로그 = 잰다("inverter_power")
    가깝나("inverter_power", 로그값(로그, "pdyn"), 100e-15 * 1.8 ** 2 * 100e6, 15,
          "P = C*V^2*f (남는 몫이 단락 전력이다)")
    ok(로그값(로그, "pdyn") > 100e-15 * 1.8 ** 2 * 100e6,
       "**잰 값이 CV^2f 보다 크다** -- 그 차이가 단락 전력이다")

    잰것, _ = 잰다("transmission_gate")
    ron = [잰것["ron_lo"], 잰것["ron_mid"], 잰것["ron_hi"]]
    ok(max(ron) / min(ron) < 4,
       f"**양 끝에서도 켜져 있다** (NMOS 혼자면 위가, PMOS 혼자면 아래가 죽는다): "
       f"{min(ron):.0f}~{max(ron):.0f}ohm")
    ok(잰것["ron_mid"] == max(ron), "가운데서 가장 세다 -- 교과서의 그 언덕")

    잰것, _ = 잰다("elmore")
    t = [잰것[f"t_len{n}"] for n in (1, 2, 4, 8)]
    가깝나("elmore/1칸", t[0], 0.69 * 1e3 * 1e-12, 5, "한 칸은 0.69*RC")
    for i in range(3):
        ok(t[i + 1] / t[i] > 2.5,
           f"**길이를 2배 하면 지연이 {t[i+1]/t[i]:.2f}배** -- 선형이면 2배다")
    ok(t[3] / t[0] > 20, f"1칸 -> 8칸이 {t[3]/t[0]:.0f}배 (선형이면 8배)")

    잰것, _ = 잰다("sram_read_disturb")
    ok(잰것["v_hold"] < 0.05, f"읽기 전에는 0 을 잡고 있다: {잰것['v_hold']:.3g} V")
    ok(0.18 < 잰것["v_disturb"] < 0.28,
       f"**읽는 동안 0 노드가 뜬다 -- 뜨되 트립점을 안 넘는다**: {잰것['v_disturb']:.3f} V")
    # **셀 비가 방해를 정한다.** 이 의존이 없으면 드라이버를 좁혀도 검사가 안 빨개진다
    # (실측: W 4u->2u 로 바꿔도 살아남았다 -- 범위가 헐렁했다).
    좁힌것 = (spice.본보기["sram_read_disturb"]
            .replace("MNL ql qr 0   0   nch W=4u", "MNL ql qr 0   0   nch W=2u")
            .replace("MNR qr ql 0   0   nch W=4u", "MNR qr ql 0   0   nch W=2u"))
    r2 = spice.돌리기(좁힌것, 초=180)
    약한것 = (r2["잰것"] or {}).get("v_disturb", 0)
    ok(약한것 > 잰것["v_disturb"] * 1.3,
       f"**셀 비를 2 에서 1 로 낮추면 방해가 커진다**: "
       f"{잰것['v_disturb']:.3f} V -> {약한것:.3f} V (드라이버를 좁힌 대가)")
    ok(잰것["v_high"] > 1.7, f"1 노드는 그대로다: {잰것['v_high']:.3g} V")

    # **초기 상태를 둘 다 빼면 셀이 반대로 앉는다.** `.ic` 하나만 빼거나 `uic` 하나만
    # 빼는 것은 결과가 똑같아서(실측) 반례가 될 수 없다 -- 그건 미해결이 아니라 동등이다.
    # 진짜 의존은 "둘 중 하나는 있어야 한다" 이고, 그것을 여기 못 박는다.
    맨것 = (spice.본보기["sram_read_disturb"]
          .replace(".ic v(ql)=0 v(qr)=1.8", "* none")
          .replace("tran 10p 10n uic", "tran 10p 10n"))
    r = spice.돌리기(맨것, 초=180)
    뒤집힘 = (r["잰것"] or {}).get("v_hold", 0)
    ok(뒤집힘 > 1.0,
       f"**초기 상태를 둘 다 빼면 셀이 반대로 앉는다** (v_hold {뒤집힘:.3g} V) -- "
       "`.ic` 나 `uic` 중 하나는 있어야 한다")

    print("\n[저장빠짐] `save` 없이 스윕에서 소자값을 읽으면 조용히 틀린다")
    # **장치가 `돌리기` 에 실제로 물려 있나.** 함수만 따로 불러 보면 이 배선이 안 검사된다
    # (실측: `빠진 = []` 로 장치를 꺼도 아무 검사가 안 빨개졌다).
    막힌것 = spice.돌리기("* t\nV1 a 0 DC 1\nR1 a 0 1k\n.control\n"
                      "dc V1 0 1 0.1\nlet x=@m1[gm]\nprint x\n.endc\n", 초=30)
    ok(막힌것["판정"] == spice.못잼 and "save" in 막힌것["왜"],
       f"**`돌리기` 가 그것 때문에 못잼을 낸다**: {막힌것['판정']} -- {막힌것['왜'][:50]}")
    ok(막힌것["로그"] == "", "돌리지도 않는다 -- 돌리면 틀린 곡선이 돌아온다")

    ok(bool(spice.저장빠짐("* t\n.control\ndc V1 0 1 0.1\nlet x=@m1[gm]\n.endc\n")),
       "**save 없는 스윕 읽기를 잡는다**")
    ok(not spice.저장빠짐("* t\n.control\nsave @m1[gm]\ndc V1 0 1 0.1\nlet x=@m1[gm]\n.endc\n"),
       "save 가 있으면 안 잡는다")
    ok(not spice.저장빠짐("* t\n.control\nop\nprint @m1[gm]\n.endc\n"),
       "스윕이 없으면 안 잡는다 (op 의 스칼라는 맞다)")
    ok(not spice.저장빠짐("* t\n.control\ndc V1 0 1 0.1\nalter @V1[acmag]=0\n.endc\n"),
       "**`alter` 는 읽기가 아니다** -- 처음엔 이것까지 걸어 거짓 못잼을 냈다")
    ok(bool(spice.저장빠짐("* t\n.control\nsave all\ndc V1 0 1 0.1\nlet x=@m1[gm]\n.endc\n")),
       "`save all` 만으로는 소자값이 안 담긴다")
    걸린것 = [n for n in spice.본보기 if spice.저장빠짐(spice.본보기[n])]
    ok(not 걸린것, f"**본보기가 하나도 안 걸린다**: {걸린것}")

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
# 2b. 몬테카를로 -- **안 흔들린 것을 '다 통과' 로 세지 않는다**
#
# 여기 거짓 초록은 하나다. 이름을 틀리거나 `.param` 이 없으면 바꿔 끼우기가 조용히
# 아무것도 안 하고, **같은 판을 N 번 돌린 뒤 "30판 다 통과, 수율 100%"** 가 나온다.
# ---------------------------------------------------------------------------
print("\n[몬테카를로] 안 흔들린 판")
넷 = spice.본보기["mc_mirror"]
ok(spice.파람값(넷, "vtn2") == 0.5, f"`.param` 값을 읽는다: {spice.파람값(넷, 'vtn2')}")
ok(spice.파람값(넷, "없는것") is None, "없는 이름은 None")
새글, 수 = spice.파람바꾸기(넷, "vtn2", 0.52)
ok(수 == 1 and spice.파람값(새글, "vtn2") == 0.52, f"값을 바꿔 끼운다: {수}자리")
ok(spice.파람바꾸기(넷, "없는것", 0.1)[1] == 0,
   "**없는 이름은 0자리 바뀐다** -- 이것을 안 세면 같은 판을 N 번 돌린다")

r = spice.흩뿌리기(넷, "없는파람 0.02", 5, "iout 4e-5 6e-5", 초=60)
ok(r["판정"] == spice.못잼,
   f"**`.param` 이 없는 이름을 흔들라면 돌리지 않는다**(수율 100% 가 나올 자리다): {r['판정']}")
ok(r["판수"] == 0, f"한 판도 안 돌린다: {r['판수']}")
ok(spice.흩뿌리기(넷, "", 5, "iout 4e-5 6e-5", 초=30)["판정"] == spice.못잼,
   "**산포를 안 주면 못잼** -- 그것은 같은 판을 N 번 돌리는 것이다")

ok(spice.산포읽기("a 0.1\nb 2e-3")== [("a", 0.1), ("b", 0.002)], "산포 줄을 읽는다")
ok(spice.산포읽기("망가진 줄 셋") == [], "이상한 줄은 버린다")

if spice.있나():
    print("\n[몬테카를로] 진짜로 흩뿌린다")
    r = spice.흩뿌리기(넷, "vtn2 0.02", 20, "iout 4e-5 6e-5", 초=120)
    ok(r["판수"] == 20, f"20판을 돈다: {r['판수']}")
    s2 = (r["흩어짐"] or {}).get("iout") or {}
    ok(s2.get("시그마", 0) > 1e-6,
       f"**결과가 실제로 흩어진다** (안 흩어지면 아무것도 안 먹은 것이다): σ={s2.get('시그마')}")
    ok(s2["최소"] < s2["최대"], "최소와 최대가 다르다")
    # 손계산: σ(Id)/Id ≈ 2σ(Vth)/Vov, Vov = sqrt(2·Id/(K'·W/L)) = 0.2236 V
    바람 = 2 * 0.02 / math.sqrt(2 * 50e-6 / (200e-6 * 10)) * 50e-6
    ok(abs(s2["시그마"] - 바람) / 바람 < 0.35,
       f"σ(Iout)={s2['시그마']:.3g} vs 손계산 {바람:.3g} (2σVth/Vov·Id)")
    ok(r["판정"] == spice.FAIL and 0 < r["수율"] < 100,
       f"일부가 탈락한다 -- 수율이 100 도 0 도 아니다: {r['수율']}")

    # σ 를 10배 줄이면 흩어짐도 10배 준다. 진짜로 흔들고 있다는 증거다.
    r2 = spice.흩뿌리기(넷, "vtn2 0.002", 20, "iout 4.8e-5 5.2e-5", 초=120)
    s3 = (r2["흩어짐"] or {}).get("iout") or {}
    비 = s2["시그마"] / max(s3["시그마"], 1e-30)
    ok(5 < 비 < 20,
       f"**σ(Vth) 를 10배 줄이면 σ(Iout) 도 10배 준다** (비 {비:.1f}) -- 씨만 바꾼 게 아니다")
    ok(r2["판정"] == spice.PASS, f"좁은 산포는 다 통과: {r2['판정']}")
    ok("3의 규칙" in r2["왜"],
       f"**0 탈락을 ±0% 로 적지 않는다** -- 3의 규칙을 댄다: {r2['왜'][:60]}")

    # **`.param` 은 있는데 아무 데도 안 쓰이는 판.** 실제로 잘 나는 실수다(이름 오타 ·
    # 모델에서 `{name}` 을 안 씀). 흔들기는 하는데 결과가 하나도 안 흩어진다 --
    # 그것을 통과로 세면 "30판 다 통과, 수율 100%" 라는 거짓 초록이 된다.
    안닿는것 = 넷.replace(".param vtn2 = 0.5",
                       ".param vtn2 = 0.5\n.param unused = 1.0")
    r0 = spice.흩뿌리기(안닿는것, "unused 0.3", 6, "iout 4e-5 6e-5", 초=90)
    ok(r0["판정"] == spice.못잼,
       f"**흔들었는데 결과가 안 흩어지면 못잼** -- 같은 판을 6번 돌린 것이다: {r0['판정']}")
    ok("안 흩어졌다" in r0["왜"], f"까닭이 그것을 말한다: {r0['왜'][:60]}")

    r3 = spice.흩뿌리기(넷, "vtn2 0.02", 20, "", 초=120)
    ok(r3["판정"] == spice.못잼 and r3["수율"] == -1,
       f"**확인 범위가 없으면 수율을 말하지 않는다** -- 흩어짐만 낸다: {r3['판정']}")

    # 씨가 같으면 같은 답. 검사가 흔들리면 그 검사는 못 쓴다.
    a = spice.흩뿌리기(넷, "vtn2 0.02", 8, "iout 4e-5 6e-5", 씨=7, 초=90)
    b = spice.흩뿌리기(넷, "vtn2 0.02", 8, "iout 4e-5 6e-5", 씨=7, 초=90)
    ok(a["수율"] == b["수율"] and a["흩어짐"]["iout"]["평균"] == b["흩어짐"]["iout"]["평균"],
       "**씨가 같으면 답이 같다** -- 안 그러면 이 검사가 날마다 다른 말을 한다")

    print("\n[노이즈] sqrt(kT/C) -- 저항값과 무관하다")
    r = spice.돌리기(spice.본보기["rc_noise"], 초=90)
    ok(r["판정"] == spice.PASS, f"노이즈 해석이 돈다: {r['판정']} -- {r['왜']}")
    on = (r["잰것"] or {}).get("onoise_total")
    이론 = math.sqrt(1.380649e-23 * 300.15 / 1e-9)
    ok(on is not None and abs(on - 이론) / 이론 < 0.05,
       f"onoise={on:.5g} vs sqrt(kT/C)={이론:.5g} -- R 이 지워진다")

# ---------------------------------------------------------------------------
# 3. 배선 -- 봇이 실제로 쓸 수 있나, 배포가 깔아 주나
# ---------------------------------------------------------------------------
print("\n[배선]")
도구글 = (뿌리 / "bot_tools.py").read_text(encoding="utf-8")
서버 = (뿌리 / "discord_bot_server.py").read_text(encoding="utf-8")
공개 = (뿌리 / "main_public.py").read_text(encoding="utf-8")
for 도구 in ("run_spice", "spice_example", "monte_carlo"):
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
