// **밤새 도는 것을 띄우기 전에 돌린다.**
//
// 왜 이렇게 검증하는가. 사람 없이 도는 물건은 "돌아간다" 를 확인하기가 어렵다 --
// 한 번 돌려 보고 잘 되면 그것은 잘 되는 경로 하나를 본 것일 뿐이고, 새벽 2시에
// 무너지는 것은 대개 안 본 경로다. 그래서 **경로를 나눠서 각각 무너뜨려 본다.**
//
// 두 단계다.
//   1) 차원별로 따로 찾는다 -- 멈춤 · 죽음 · 데이터 손상 · 자원 누수 · 배선 · 한도.
//      한 사람에게 "다 봐라" 하면 제일 눈에 띄는 것만 보고 나머지는 안 본다.
//   2) 찾은 것마다 **반증**을 붙인다. "이미 다른 데서 막고 있지 않은가,
//      그 경로가 실제로 타기는 하는가" 를 따로 확인하고, 확실하지 않으면 버린다.
//      그러지 않으면 그럴듯하지만 틀린 지적이 목록에 남아 진짜를 덮는다.
//
// 쓰는 법:
//   Workflow({ name: "verify-unattended-loop" })
// 고칠 데가 생기면 DIMENSIONS 에 차원을 더하거나 REPO 를 바꾼다.
// **Gemini 쿼터를 안 쓴다** -- 여기서 도는 것은 코드 리뷰이고 소설 호출이 아니다.

export const meta = {
  name: 'verify-unattended-loop',
  description: 'DRIFT 학습 자동화가 밤새 안 끊기는지 적대적으로 검증한다',
  phases: [
    { title: 'Find', detail: '차원별로 실패 모드를 찾는다' },
    { title: 'Verify', detail: '찾은 것을 반증해 본다' },
  ],
}

const REPO = '/home/user/SE'

const DIMENSIONS = [
  {
    key: 'stall',
    prompt: `${REPO} 의 scripts/run_all.sh, scripts/tune_loop.sh, scripts/preflight.sh 를 읽어라.
이 스크립트들은 사람 없이 밤새 도는 것이 목적이다(setsid nohup 으로 띄운다).
**루프가 영원히 멈추거나(hang) 무한히 도는(spin) 자리**만 찾아라.
특히: pgrep 패턴이 자기 자신을 잡는가, while 루프의 탈출 조건이 실제로 성립하는가,
drift.sh 가 백그라운드로 띄우고 즉시 돌아오는데 기다리는 방식이 맞는가,
STOP 파일이 모든 루프에서 실제로 검사되는가, sleep 이 걸린 채 영원히 대기하는 경로가 있는가.
파일:줄번호와 함께, 어떤 입력/상태에서 실제로 그렇게 되는지 구체적으로 적어라.`,
  },
  {
    key: 'crash',
    prompt: `${REPO} 의 novel/tuner.py, novel/arms.py, novel/score.py, novel/profile.py 를 읽어라.
이것들은 밤새 도는 루프가 바퀴마다 부른다. **예외로 죽는 자리**를 찾아라.
특히: 파일이 없거나 비었을 때, JSON 이 깨졌을 때, chunks 가 빈 배열일 때,
division by zero, KeyError, 리스트 인덱스, subprocess timeout, claude -p 가 없을 때.
죽으면 루프가 그 바퀴를 건너뛰는지 통째로 서는지도 함께 판단해라.
파일:줄번호와 재현 조건을 구체적으로.`,
  },
  {
    key: 'corrupt',
    prompt: `${REPO} 의 novel/tuner.py 와 novel/dyn.py, novel/directives.json, novel/targets.json 을 읽어라.
튜너는 directives.json 을 고쳐 쓰고, 점수가 나빠지면 되돌린다.
**데이터가 조용히 망가지는 자리**를 찾아라. 특히:
- 되돌리기(keep)가 실제로 이전 값을 복원하는가? 여러 번 고친 뒤에도?
- claude -p 가 이상한 것을 돌려줬을 때 그대로 써 넣는가?
- format 자리표({got} {lo} {hi} {mid} {n_climb} {climb_words})가 없거나 다른 이름이면 어떻게 되는가?
  dyn.asks 가 .format 을 부르는데 지시문에 모르는 자리표가 있으면?
- 동시에 두 프로세스가 같은 파일을 쓰면?
파일:줄번호와 함께 구체적으로.`,
  },
  {
    key: 'resource',
    prompt: `${REPO} 를 보고 **밤새 돌 때 자원이 새는 자리**를 찾아라.
- 디스크: logs/, novel/*.json, logs/tune/ 백업이 무한히 쌓이는가? 정리 로직이 실제로 도는가?
- 원고 크기: drift.json 의 chunks 와 arms 배열이 계속 커지는데, 그것을 매 덩어리 읽고 쓰면?
- 메모리/시간: profile.py 가 원고 전체를 매번 재는가? 덩어리가 100개면?
scripts/tune_loop.sh 의 KEEP 로직(ls -1t | tail -n +N | xargs rm)이 파일이 없을 때도 안전한가?
파일:줄번호와 함께.`,
  },
  {
    key: 'wiring',
    prompt: `${REPO} 의 novel/flow.py, novel/compose.py, novel/spine.py, novel/plot.py 를 읽어라.
프롬프트를 짓는 경로다. **실제로 안 이어져 있는 배선**을 찾아라.
- compose.build 가 받는 인자를 flow.write_prompt 가 다 채우는가?
- book["_arm"] 이 설정되는 자리와 읽히는 자리가 실제로 이어지는가? 첫 덩어리에서는?
- spine.brief 가 파일을 매번 읽는가(덩어리마다 디스크 접근)?
- DRIFT_PROMPT=axes 일 때 owed_brief/ahead_brief/feedback 이 실제로 전달되는가?
- 원장(ledger)이 비었을 때 프롬프트가 말이 되는가?
파일:줄번호와 함께.`,
  },
  {
    key: 'quota',
    prompt: `${REPO} 의 scripts/quota_show.py, orchestrator/llm_pool.py, scripts/tune_loop.sh 를 읽어라.
**한도(쿼터) 처리가 밤새 도는 것을 망치는 자리**를 찾아라.
- quota_show.py --brief 의 종료 코드 3 이 tune_loop 의 until 루프와 올바로 맞물리는가?
- 키가 아예 없을 때 --brief 는 무엇을 하는가? 루프는?
- 모든 후보가 소진이면 몇 시간을 어떻게 기다리는가? 그 사이 STOP 이 먹히는가?
- 429 가 계속 날 때 루프가 조용히 빈 원고를 쌓는가?
파일:줄번호와 함께.`,
  },
]

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'number' },
          scenario: { type: 'string' },
          impact: { type: 'string', enum: ['stops-the-loop', 'wastes-a-round', 'corrupts-data', 'cosmetic'] },
          fix: { type: 'string' },
        },
        required: ['title', 'file', 'scenario', 'impact', 'fix'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT = {
  type: 'object',
  properties: {
    real: { type: 'boolean' },
    why: { type: 'string' },
  },
  required: ['real', 'why'],
}

phase('Find')
const results = await pipeline(
  DIMENSIONS,
  d => agent(d.prompt, { label: `find:${d.key}`, phase: 'Find', schema: FINDINGS }),
  (res, d) => {
    const found = (res && res.findings) || []
    if (!found.length) return []
    return parallel(found.slice(0, 8).map(f => () =>
      agent(`${REPO} 저장소에서 아래 주장을 **반증해라.** 코드를 직접 읽고 확인해라.

주장: ${f.title}
파일: ${f.file}${f.line ? ':' + f.line : ''}
어떤 상황에서: ${f.scenario}

이 주장이 틀렸다고 볼 근거를 먼저 찾아라. 이미 다른 데서 막고 있거나, 그 코드 경로가
실제로는 안 타거나, 조건이 성립할 수 없으면 real=false 다. 확실하지 않으면 real=false.
정말로 밤새 도는 루프를 망가뜨릴 수 있을 때만 real=true.`,
        { label: `verify:${d.key}:${f.title.slice(0, 20)}`, phase: 'Verify', schema: VERDICT })
      .then(v => (v && v.real ? { ...f, why: v.why } : null))))
  },
)

const confirmed = results.flat().filter(Boolean)
const order = { 'stops-the-loop': 0, 'corrupts-data': 1, 'wastes-a-round': 2, cosmetic: 3 }
confirmed.sort((a, b) => (order[a.impact] ?? 9) - (order[b.impact] ?? 9))
log(`확인된 것 ${confirmed.length}개`)
return { confirmed }
