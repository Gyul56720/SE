# policy_core -- OS-독립 능동탐색 정책 코어.
# host_test: 데스크톱서 코어를 돌려 창발·RTA·belief 를 붙든다(회귀).
# 코어(policy_core.c)는 OS/센서/차량 의존 없음 -> MCU 크로스컴파일로 그대로 이식.
CC      ?= gcc
CFLAGS  ?= -std=c99 -O2 -Wall -Wextra -Werror
LDLIBS  ?= -lm

host_test: host_test.c policy_core.c policy_core.h
	$(CC) $(CFLAGS) -o $@ host_test.c policy_core.c $(LDLIBS)

# sim: Phase-1 측정 -- 6 정책을 같은 시뮬레이터로 돌려 성공률·시간·거리·전환·RTA 표
sim: sim.c policy_core.c policy_core.h
	$(CC) $(CFLAGS) -o $@ sim.c policy_core.c $(LDLIBS)

.PHONY: test baselines clean
test: host_test
	./host_test

baselines: sim
	./sim

clean:
	rm -f host_test sim

# MCU 이식 예 (코어만, host_test 제외):
#   arm-none-eabi-gcc -std=c99 -Os -mcpu=cortex-m4 -c policy_core.c
# policy_core.c 는 stdio 를 안 쓴다 -> bare-metal 링크 가능. math 는 libm/근사로 대체.
