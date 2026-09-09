# 받아 둔 원장이 들어오는 자리

`*.json` 은 **추적하지 않는다**(`.gitignore`). 여기 신선도는 며칠짜리라
(`brief/source.py` 의 `신선`), 커밋해 두면 관문 **B003(낡은 원장)** 이 매번 걸린다.

```bash
python3 brief/report.py 주식 --것 코스피,나스닥 --저장 brief/ledger/주식.json
python3 brief/report.py 주식 --원장 brief/ledger/주식.json     # 안 받고 그것으로
```

## 꼴

`출처` 와 `받은날` 이 **없으면 `ledger.load()` 가 안 읽는다.** 언제 어디서 온 것인지
모르는 원장은 못 쓴다 — 그 위에서 낸 수는 무엇의 수인지 아무도 모른다.

```json
{
 "출처": "주식",
 "받은날": "2026-09-09",
 "질의": "https://stooq.com/q/l/?s=^kospi,^ndq&f=sd2t2ohlcv&h&e=csv",
 "줄": [{"id": "^kospi", "Date": "2026-09-09", "Open": 2500.0, "High": 2530.0,
         "Low": 2480.0, "Close": 2510.0, "Volume": 412000.0}],
 "버린것": 0
}
```

`id` 는 출처가 정한 `key` 칸에서 온다. 관문 **B002** 가 보고서의 수를 이 `id` 로
되짚으므로, `id` 없는 줄은 실리지 않는다.
