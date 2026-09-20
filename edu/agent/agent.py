# -*- coding: utf-8 -*-
"""24시간 회귀 에이전트 -- 돌리고, 걸리면 좁히고, 고쳐 보고, 기록한다.

## 무엇을 하나

    블록마다 무한 반복:
      1. 자해검사   비교가 무는지 먼저 본다.  안 물면 그 바퀴 결과는 버린다
      2. 회귀       씨앗을 바꿔 가며 골든모델과 비교한다
      3. 좁히기     걸리면 실패 자극 하나로 재현한다
      4. 수리       한 곳만 바꾼 편집을 찾아 본다 (vrepair)
      5. 적용/보고  받아들인 편집만 파일에 쓴다.  못 고치면 보고만 한다

## 사람에게 무엇을 남기나

    원장 (JSONL)   바퀴마다 한 줄.  씨앗·시행·틀림·서로다른출력·수리결과
    상태 (JSON)    지금 무엇을 하고 있나.  다음 세션이 추측하지 않고 읽는다
    패치 (diff)    적용한 편집마다 하나.  `git diff` 로 볼 수 있게

## 왜 '적용' 이 기본이 아닌가

`--적용` 을 주지 않으면 **파일을 고치지 않는다**.  자동 수리가 통과시킨 편집이
의미상 맞다는 보장은 없다 -- 세 관문(원래 씨앗 · 안 쓴 씨앗 · 자해검사)은
*증거*이지 *증명*이 아니다.  기본을 보고로 두고, 적용은 사람이 켠다.

## 원장 자리

`SE_LEDGER_ROOT` 를 보면 거기에 쓴다.  없으면 `agent/ledger/`.  이 저장소가
겪은 사고(검사가 진짜 원장을 더럽힘) 때문에 **환경 변수로** 받는다 -- 깃발은
손자 프로세스까지 안 내려간다.
"""
import os, sys, json, time, argparse, importlib.util, random, traceback, signal

여기 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 여기)
import harness, vrepair

멈춤 = {"값": False}


def _신호(sig, frame):
    멈춤["값"] = True


def 원장자리():
    r = os.environ.get("SE_LEDGER_ROOT")
    d = os.path.join(r, "verif") if r else os.path.join(여기, "ledger")
    os.makedirs(d, exist_ok=True)
    return d


def 블록들(고른것=None):
    루트 = os.path.join(여기, "blocks")
    out = []
    for 이름 in sorted(os.listdir(루트)):
        p = os.path.join(루트, 이름, "block.py")
        if not os.path.exists(p):
            continue
        if 고른것 and 이름 not in 고른것:
            continue
        spec = importlib.util.spec_from_file_location(f"blk_{이름}", p)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
        except Exception as e:
            print(f"[건너뜀] {이름}: {e}", flush=True)
            continue
        out.append(m)
    return out


def 적기(원장, 줄):
    with open(원장, "a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


def 한바퀴(블록, 씨앗, 시행, 적용, 원장, 패치자리):
    줄 = {"때": time.strftime("%Y-%m-%dT%H:%M:%S"), "블록": 블록.이름,
          "씨앗": 씨앗, "시행": 시행}
    ok, 왜 = harness.자해검사(블록)
    줄["자해검사"] = bool(ok)
    if not ok:
        줄["자해검사이유"] = 왜
        줄["판정"] = "검사를 믿을 수 없다"
        적기(원장, 줄)
        return 줄
    r = harness.잰다(블록, 시행=시행, 씨앗=씨앗)
    줄.update({"틀림": r.틀림, "서로다른출력": r.서로다른출력,
               "초": round(r.초, 2), "오류": r.오류})
    if r.오류:
        줄["판정"] = "실행 실패"
        적기(원장, 줄)
        return 줄
    if not r.쓸모있나:
        줄["판정"] = "자극이 DUT 를 안 건드렸다 -- 초록이라도 뜻이 없다"
        적기(원장, 줄)
        return 줄
    if not r.틀림:
        줄["판정"] = "초록"
        적기(원장, 줄)
        return 줄
    # 빨간불
    줄["첫실패"] = r.첫실패
    줄["최소사례"] = harness.좁히기(블록, r.첫실패, 씨앗)
    수리 = vrepair.고쳐보기(블록, harness, 씨앗=씨앗,
                          검증씨앗=씨앗 + 100003, 시행=시행)
    줄["수리"] = {k: v for k, v in 수리.items() if k != "원문"}
    if 수리.get("실패"):
        줄["판정"] = "빨간불 -- 수리 실패, 사람이 봐야 한다"
    elif not 적용:
        줄["판정"] = "빨간불 -- 수리 후보 있음 (적용 안 함; --적용 을 줘라)"
    else:
        파일 = 블록.소스들()[0]
        전문 = open(파일, encoding="utf-8").read()
        open(파일, "w", encoding="utf-8").write(수리["원문"])
        pn = os.path.join(패치자리,
                          f"{블록.이름}_{time.strftime('%Y%m%d_%H%M%S')}.patch")
        with open(pn, "w", encoding="utf-8") as f:
            f.write(f"# {블록.이름} 줄 {수리['줄번호']}  규칙: {수리['규칙']}\n")
            f.write(f"# 왜 이 규칙인가: {수리['왜']}\n")
            f.write(f"-{수리['전']}\n+{수리['후']}\n")
        줄["패치"] = pn
        줄["판정"] = "빨간불 -- 수리 적용됨"
        # 적용 후 다시 잰다.  적용했다고 초록이라고 말하지 않는다
        r2 = harness.잰다(블록, 시행=시행, 씨앗=씨앗 + 7)
        줄["적용후틀림"] = r2.틀림
        if r2.틀림:
            open(파일, "w", encoding="utf-8").write(전문)
            줄["판정"] = "빨간불 -- 적용했다가 되돌림 (적용 후에도 틀림)"
    적기(원장, 줄)
    return 줄


def 본체(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--시간", type=float, default=24.0, help="몇 시간 돌릴지")
    ap.add_argument("--시행", type=int, default=4000)
    ap.add_argument("--블록", nargs="*", default=None)
    ap.add_argument("--적용", action="store_true",
                    help="받아들인 편집을 파일에 쓴다 (기본은 보고만)")
    ap.add_argument("--씨앗시작", type=int, default=0)
    ap.add_argument("--쉼", type=float, default=0.0, help="바퀴 사이 초")
    a = ap.parse_args(argv)

    signal.signal(signal.SIGTERM, _신호)
    signal.signal(signal.SIGINT, _신호)

    d = 원장자리()
    원장 = os.path.join(d, "regress.jsonl")
    상태파일 = os.path.join(d, "status.json")
    패치자리 = os.path.join(d, "patches")
    os.makedirs(패치자리, exist_ok=True)

    bs = 블록들(a.블록)
    if not bs:
        print("블록이 없다", flush=True)
        return 2
    끝 = time.time() + a.시간 * 3600
    씨앗 = a.씨앗시작
    셈 = {"바퀴": 0, "초록": 0, "빨강": 0, "수리적용": 0, "수리실패": 0,
          "검사못믿음": 0}
    print(f"시작: 블록 {len(bs)}개, {a.시간}시간, 원장 {원장}", flush=True)
    while time.time() < 끝 and not 멈춤["값"]:
        for b in bs:
            if time.time() >= 끝 or 멈춤["값"]:
                break
            try:
                줄 = 한바퀴(b, 씨앗, a.시행, a.적용, 원장, 패치자리)
            except Exception:
                줄 = {"블록": b.이름, "씨앗": 씨앗, "판정": "에이전트 예외",
                      "역추적": traceback.format_exc()[-1500:]}
                적기(원장, 줄)
            셈["바퀴"] += 1
            p = 줄.get("판정", "")
            if p == "초록":
                셈["초록"] += 1
            elif "검사를 믿을 수 없다" in p:
                셈["검사못믿음"] += 1
            elif "적용됨" in p:
                셈["빨강"] += 1; 셈["수리적용"] += 1
            elif "빨간불" in p:
                셈["빨강"] += 1; 셈["수리실패"] += 1
            json.dump({"갱신": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "남은초": int(끝 - time.time()), "씨앗": 씨앗,
                       "마지막": 줄.get("판정"), "블록": 줄.get("블록"),
                       "셈": 셈},
                      open(상태파일, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            if a.쉼:
                time.sleep(a.쉼)
        씨앗 += 1
    print(json.dumps(셈, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(본체())
