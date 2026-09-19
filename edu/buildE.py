# -*- coding: utf-8 -*-
"""Assemble and render the English textbook."""
import sys, os, importlib
sys.path.insert(0, "/home/user/SE/edu")
from bookE import cover, toc, render, zoo, E, read, ZOO
import srcsel, srcdocE, apidoc, bookE

Z, BY = zoo()
NF = sum(len(v) for v in Z.values())
NL = sum(f["줄"] for v in Z.values() for f in v)

# ----------------------------------------------------------------- body
def body():
    mods = [
        ("Z_found0",  ["ch_abstraction", "ch_boolean", "ch_sequential", "ch_circuits"]),
        ("A_found",   ["ch_lti", "ch_transform", "ch_sampling", "ch_prob", "ch_linalg"]),
        ("B_device",  ["ch_mos", "ch_cmos", "ch_timing", "ch_interconnect", "ch_analog"]),
        ("C_digital", ["ch_arith", "ch_control", "ch_cdc"]),
        ("D_arch",    ["ch_isa", "ch_pipeline", "ch_memory"]),
        ("E_dsp",     ["ch_filters", "ch_fft"]),
        ("F_comm",    ["ch_link", "ch_fec"]),
        ("G_rf",      ["ch_tline", "ch_radar"]),
        ("H_verif",   ["ch_verif", "ch_eda", "ch_sec"]),
        ("I_info",    ["ch_info", "ch_algebra", "ch_opt", "ch_discrete"]),
        ("J_blocks",  ["ch_memory_design", "ch_accel", "ch_noc", "ch_codec"]),
        ("K_wireless",["ch_wireless", "ch_protocol", "ch_reliability", "ch_modern"]),
        ("L_phys",    ["ch_semi", "ch_power", "ch_thermal", "ch_control"]),
        ("M_soft",    ["ch_hwsw", "ch_ml", "ch_image", "ch_measure"]),
        ("N_extra",   ["ch_async", "ch_physdes", "ch_stats", "ch_optics"]),
        ("W_practice",["ch_house", "ch_process", "ch_auto", "ch_labs",
                       "ch_papers", "ch_career", "ch_bringup", "ch_business"]),
        ("Q_more",    ["ch_queue", "ch_hls", "ch_embedded", "ch_emc"]),
        ("R_crypto",  ["ch_cryptomath", "ch_test", "ch_quantum"]),
        ("P_iface",   ["ch_mipi", "ch_pcie", "ch_gmac"]),
        ("S_iface2",  ["ch_storage", "ch_display", "ch_clocking", "ch_ipxact"]),
        ("X1_fixed",  ["ch_fixed"]),
        ("X2_timing", ["ch_sta"]),
        ("X3_cdc",    ["ch_cdc"]),
        ("X4_link",   ["ch_linkbudget"]),
        ("X5_fec",    ["ch_rs"]),
        ("X6_fft",    ["ch_fft"]),
        ("X7_power",  ["ch_power"]),
        ("X8_verif",  ["ch_verifmath"]),
        ("X9_arith",  ["ch_arith2"]),
        ("X10_mem",   ["ch_mem2"]),
        ("X11_noc",   ["ch_noc2"]),
        ("X12_ams",   ["ch_ams"]),
        ("X13_ml",    ["ch_mlhw"]),
        ("X14_physdes", ["ch_physdes2"]),
        ("X15_sec",   ["ch_hwsec"]),
        ("X16_rel",   ["ch_reliability2"]),
        ("X17_modern",["ch_modern2"]),
        ("X18_queue", ["ch_perf2"]),
        ("X19_isa",   ["ch_cores"]),
        ("X20_codec", ["ch_codec2"]),
        ("X21_control",["ch_control2"]),
        ("X22_dsp2",  ["ch_resample"]),
        ("X23_math",  ["ch_complex"]),
        ("X24_linalg",["ch_numlin"]),
        ("X25_detect",["ch_detect"]),
        ("X26_opt",   ["ch_opt2"]),
        ("X27_dft",   ["ch_dft"]),
        ("X28_cache", ["ch_cache"]),
        ("X29_ldpc",  ["ch_ldpc"]),
        ("X30_wireless", ["ch_ofdm"]),
        ("X31_analog",["ch_analog2"]),
        ("X32_pdn",   ["ch_pdn"]),
        ("X33_boolean",["ch_boolreason"]),
        ("X34_synth", ["ch_synth"]),
        ("X35_netds", ["ch_hwds"]),
        ("X36_crypto",["ch_cryptoeng"]),
        ("X37_bus",   ["ch_bus"]),
        ("X38_isp",   ["ch_isp2"]),
        ("X39_clock", ["ch_clocking2"]),
        ("X40_map",   ["ch_map"]),
        ("Y1_mipi",   ["ch_mipi2"]),
        ("Y2_pcie",   ["ch_pcie2"]),
        ("Y3_gmac",   ["ch_gmac2"]),
        ("Y4_agent",  ["ch_agent"]),
        ("Y5_business", ["ch_business2"]),
        ("Y6_papers", ["ch_papers2"]),
        ("Y7_bringup",["ch_bringup2"]),
        ("Y8_solo",   ["ch_solo"]),
        ("Y9_compliance", ["ch_compliance"]),
        ("Y10_regmap", ["ch_regmap"]),
        ("Y11_model",  ["ch_modelling"]),
        ("Y12_hls",    ["ch_hls2"]),
        ("Y13_career", ["ch_career2"]),
        ("Y14_toolchain", ["ch_toolchain"]),
        ("Y15_first90", ["ch_project"]),
    ]
    out = []
    for m, fns in mods:
        mod = importlib.import_module(m)
        importlib.reload(mod)
        for f in fns:
            h = getattr(mod, f)()
            _검사(m, f, h)
            out.append(h)
    return "\n".join(out)


상수열 = []


def _상수열찾기(모듈, 함수, h):
    """'measured' 라고 적힌 표에서 **모든 행이 같은 값인 칸**을 찾아 모아 둔다.

    실측 2026-09-19: 이 책의 FIFO 표가 드롭 0 을 여섯 줄 내리 찍고 있었는데
    본문은 "작은 FIFO 는 드롭한다" 고 적혀 있었다.  모델이 퇴화해서 큐가 아예
    안 생겼던 것이다 -- **수를 안 보고 문장을 썼다.**  글자를 보는 검사는 이것을
    못 잡는다.  그래서 수를 본다.

    상수 칸이 늘 잘못인 것은 아니다(경계 자체가 상수인 표가 있다).  그래서
    **실패로 내지 않고 빌드 끝에 목록으로 찍는다** -- 사람이 한 줄씩 본다.
    """
    import re as _re
    for 표 in _re.findall(r"<table>.*?</table>", h, _re.S):
        cap = _re.search(r"<caption>(.*?)</caption>", 표, _re.S)
        cap = _re.sub(r"<[^>]+>", "", cap.group(1)) if cap else ""
        if "easured" not in cap and "imulated" not in cap:
            continue
        몸 = _re.search(r"<tbody>(.*?)</tbody>", 표, _re.S)
        if not 몸:
            continue
        행들 = [_re.findall(r"<td>(.*?)</td>", r, _re.S)
                for r in _re.findall(r"<tr>(.*?)</tr>", 몸.group(1), _re.S)]
        행들 = [r for r in 행들 if r]
        if len(행들) < 4:
            continue
        머리 = _re.findall(r"<th>(.*?)</th>", 표, _re.S)
        폭 = min(len(r) for r in 행들)
        for c in range(1, 폭):
            값 = {_re.sub(r"<[^>]+>", "", r[c]).strip() for r in 행들}
            if len(값) == 1:
                이름 = _re.sub(r"<[^>]+>", "", 머리[c]) if c < len(머리) else f"col{c}"
                상수열.append(f"{모듈}.{함수}: \"{cap[:60]}\" 의 칸 "
                            f"\"{이름[:40]}\" 이 {len(행들)} 줄 내내 {값.pop()!r}")


def _검사(모듈, 함수, h):
    """장 하나의 HTML 이 성한지 본다 -- **빌드가 실패로 끝나게** 한다.

    안 닫힌 <div> 는 WeasyPrint 가 조용히 고쳐 주므로 렌더는 성공한다.  그런데
    그 뒤의 내용이 통째로 그 상자 안에 들어가 배경색이 몇 페이지씩 번진다.
    눈으로 1600 페이지를 보지 않을 것이므로 기계가 본다.
    """
    import re as _re
    for 태그 in ("div", "table", "figure", "pre", "h1", "h2"):
        연 = len(_re.findall(rf"<{태그}[ >]", h))
        닫 = len(_re.findall(rf"</{태그}>", h))
        assert 연 == 닫, f"{모듈}.{함수}: <{태그}> {연}개, </{태그}> {닫}개"
    if "<h1 " not in h:
        raise AssertionError(f"{모듈}.{함수}: h1 이 없다 -- 목차에 안 잡힌다")
    _상수열찾기(모듈, 함수, h)


# ------------------------------------------------------- code appendix
def code_appendix():
    groups, total, log = srcsel.고르기()
    out = ['<h1 class="srcapp" id="VOL2">Volume II &mdash; Production Source Code</h1>']
    out.append(f"""<p>This volume reproduces <b>{total:,} lines</b> of source from
    {len(groups)} blocks that are shipping in silicon or sold as commercial IP. Nothing is
    paraphrased: every line is read from disk and printed with its real line number, so a
    citation of the form <code>file:line</code> anywhere in this book can be followed
    directly.</p>
    <p>Each block is preceded by four notes &mdash; <b>What</b> it is, <b>Why</b> it
    exists (what fails without it), the <b>EECS concepts</b> it rests on, and a
    <b>practice note</b> for engineers who must work with it. An <b>API dictionary</b>
    then lists every module, class, function, parameter, port, macro and typedef that the
    block declares, with the arguments each one takes, because names alone are
    ambiguous.</p>
    <div class="note">The API dictionary is generated by pattern extraction, not by a
    full language front end. It is therefore complete enough to navigate by and may miss
    unusual declarations; the verbatim source that follows each table is authoritative.</div>""")

    for name, files in groups:
        out.append(f'<h1 class="srcapp" id="blk_{abs(hash(name))%10**8}">{E(name)}</h1>')
        d = srcdocE.D.get(name)
        if d:
            out.append(f'<div class="note"><b>What this is.</b> {d["what"]}</div>')
            out.append(f'<div class="warn"><b>Why it exists.</b> {d["why"]}</div>')
            out.append(f'<div class="bs"><b>EECS concepts.</b> {d["eecs"]}</div>')
            out.append(f'<div class="ms"><b>Practice note.</b> {d["practice"]}</div>')
        else:
            raise KeyError(f"no note for bundle: {name!r}")
        tot = sum(n for _, _, n in files)
        out.append(f'<div class="kvbar">{len(files)} files &bull; {tot:,} lines</div>')

        # --- API dictionary
        for z, rel, n in files:
            try:
                kind, api = apidoc.훑기(z, rel)
            except Exception:
                continue
            if not kind:
                continue
            order = (["module", "package", "parameter", "localparam", "port",
                      "typedef", "define"] if kind == "sv"
                     else ["namespace", "class", "function", "typedef", "define"])
            tabs = [apidoc.표로(k, api.get(k, []), bookE.tab, rel)
                    for k in order if api.get(k)]
            tabs = [t for t in tabs if t]
            if tabs:
                out.append(f'<h3>API &mdash; <code>{E(rel.split("/")[-1])}</code></h3>')
                out.extend(tabs)

        # --- verbatim source
        out.append('<div class="srcwrap">')
        for i, (z, rel, n) in enumerate(files, 1):
            t = read(z, rel)
            L = t.splitlines()
            out.append(f'<h3 class="srcfile">{i}. {E(rel)} '
                       f'<span class="srcmeta">({len(L):,} lines)</span></h3>')
            out.append('<pre class="src">' + "\n".join(
                f'<span class="ln">{k:5d}</span> {E(s)}' for k, s in enumerate(L, 1))
                + '</pre>')
        out.append('</div>')
    return "\n".join(out), total


if __name__ == "__main__":
    B = body()
    C, total = code_appendix()
    meta = f"""
<p>A graduate curriculum for the design, modelling and verification of semiconductor
IP blocks, written from first principles and grounded throughout in source code that is
shipping in production silicon.</p>
<p><b>Corpus.</b> {NF:,} files, <b>{NL:,} lines</b> of real design and modelling code were
collected and indexed mechanically. Every quantity quoted in this book is computed from
that index; none is written from memory.</p>
<p><b>How to read.</b> <span style="background:#eef7f2">Green</span> boxes recall
undergraduate material; <span style="background:#f4eefa">purple</span> boxes carry
graduate-level detail and the reasoning a practising engineer needs;
<span style="background:#fbf2f2">red</span> boxes mark places where real projects have
failed.</p>"""
    full = B + C
    front = cover("EECS-IP-001", "Semiconductor IP Design",
                  "Theory, Production Code, and the Practice of a Design House",
                  meta) + toc(full)
    doc = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
           '<title>Semiconductor IP Design</title></head><body>'
           + front + full + '</body></html>')
    render(doc, "/home/user/SE/edu/IP_Design_Textbook.pdf")
    print(f"code appendix: {total:,} lines")
    if 상수열:
        print(f"\n== 잰 표인데 칸이 상수인 곳 {len(상수열)}건 -- 한 줄씩 볼 것 ==")
        for l in 상수열:
            print("  " + l)
    else:
        print("잰 표에 상수 칸 없음")
