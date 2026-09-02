# 실행 규칙

이 폴더의 스크립트는 `.sv` 파일과 생성 파일을 **작업 디렉터리 기준 상대경로**로 참조한다.
따라서 반드시 이 폴더 안에서 실행한다.

```bash
cd npu
python3 npu_hi_sim.py        # iverilog 로 빌드 -> vvp 로 실행
```

루트에서 `python3 npu/npu_hi_sim.py`로 돌리면 `npu_axi_top.sv`를 찾지 못한다.
`vvp` 산출물(`hi_sim`, `array_sim` 등)과 `array_*.txt`는 재생성되므로 커밋하지 않는다.
