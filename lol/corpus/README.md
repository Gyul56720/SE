# 경기 원장이 들어오는 자리

`*.jsonl` 은 **추적하지 않는다**(`.gitignore`). `law/corpus/*.txt` 와 같은 이유이고,
여기서는 더 급하다 — 조문은 몇 달 그대로지만 **레이팅은 어제 경기 하나로 바뀐다.**
커밋해 두면 낡은 승률이 정답 자리에 남는다.

받는 법:

```bash
python3 lol/fetch.py --진단 --대회 'LCK/2026 Season'    # 받되 저장 안 한다
python3 lol/fetch.py --대회 'LCK/2026 Season'
python3 lol/fetch.py --파일 내려받은것.csv --출처 'Oracle Elixir'
```

## 꼴

첫 줄이 **머리글**이고, 머리글이 없는 파일은 `corpus.load()` 가 **안 읽는다.**
언제 것인지 모르는 원장은 못 쓴다.

```
{"_원장":"lol","받은날":"2026-09-09","출처":"lol.fandom.com Cargo ScoreboardGames","질의":"...","경기수":412}
{"date":"2026-01-15 09:00:00","blue":"T1","red":"Gen.G","winner":"T1","tournament":"LCK/2026","patch":"16.1"}
```

`winner` 는 `blue` 나 `red` 와 **글자 그대로 같아야 한다.** 아니면 그 줄은 안 실린다 —
무승부·몰수·미기록을 0.5 로 세거나 blue 로 세면 레이팅이 조용히 기운다.
