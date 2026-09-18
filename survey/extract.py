"""Structural extractor: every file, every function, every pragma. Nothing skipped."""
import json, os, re, collections

ROOT = "/home/user/hls_study"
GROUPS = {
    "Vitis_solver": "AMD Vitis Libraries - Solver (Apache-2.0)",
    "Vitis_solver_L2": "AMD Vitis Libraries - Solver L2 (Apache-2.0)",
    "Vitis_security": "AMD Vitis Libraries - Security (Apache-2.0)",
    "Vitis_dsp_fft": "AMD Vitis Libraries - DSP/FFT (Apache-2.0)",
    "finn_hlslib": "Xilinx FINN-hlslib (BSD-3-Clause)",
}

RE_INC   = re.compile(r'#\s*include\s+[<"]([^>"]+)[>"]')
RE_PRAG  = re.compile(r'#\s*pragma\s+HLS\s+(.+)')
RE_TMPL  = re.compile(r'^\s*template\s*<', re.M)
RE_CLASS = re.compile(r'^\s*(class|struct)\s+([A-Za-z_]\w*)', re.M)
RE_FUNC  = re.compile(
    r'^\s*(?:static\s+|inline\s+|constexpr\s+|virtual\s+)*'
    r'([A-Za-z_][\w:<>,\s\*&\.]*?)\s+'
    r'([A-Za-z_]\w*)\s*\(', re.M)
RE_DEF   = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)', re.M)
RE_LABEL = re.compile(r'^\s*([A-Za-z_]\w*)\s*:\s*$', re.M)
TYPES = ("ap_uint<", "ap_int<", "ap_fixed<", "ap_ufixed<", "hls::stream<",
         "hls::x_complex<", "std::complex<", "ap_shift_reg", "decltype")
KEYWORDS = {"if","for","while","switch","return","sizeof","catch","do","else"}

def header_comment(text):
    m = re.match(r'\s*/\*(.*?)\*/', text, re.S)
    if not m: return ""
    body = m.group(1)
    body = re.sub(r'^\s*\*\s?', '', body, flags=re.M)
    return body.strip()

def license_of(text):
    h = text[:2500]
    if "Apache License" in h: return "Apache-2.0"
    if "Redistribution and use in source and binary forms" in h: return "BSD-3-Clause"
    return "unknown"

files = []
for g in sorted(GROUPS):
    d = os.path.join(ROOT, g)
    if not os.path.isdir(d): continue
    for dirpath, _, names in os.walk(d):
        for n in sorted(names):
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, ROOT)
            text = open(p, encoding="utf-8", errors="replace").read()
            lines = text.splitlines()
            prag = collections.Counter()
            prag_lines = []
            for i, ln in enumerate(lines, 1):
                m = RE_PRAG.search(ln)
                if m:
                    body = m.group(1).strip()
                    key = body.split()[0].upper() if body.split() else "?"
                    prag[key] += 1
                    prag_lines.append({"line": i, "text": body[:120]})
            funcs = []
            for m in RE_FUNC.finditer(text):
                name = m.group(2)
                if name in KEYWORDS: continue
                ret = " ".join(m.group(1).split())
                if len(ret) > 60: ret = ret[:57] + "..."
                ln = text[:m.start()].count("\n") + 1
                funcs.append({"line": ln, "ret": ret, "name": name})
            seen, ufuncs = set(), []
            for f in funcs:
                k = (f["name"], f["ret"])
                if k in seen: continue
                seen.add(k); ufuncs.append(f)
            files.append({
                "group": g, "rel": rel, "name": n,
                "lines": len(lines), "bytes": len(text),
                "license": license_of(text),
                "header": header_comment(text)[:1500],
                "includes": sorted(set(RE_INC.findall(text))),
                "templates": len(RE_TMPL.findall(text)),
                "classes": [{"kind": k, "name": v} for k, v in RE_CLASS.findall(text)],
                "defines": sorted(set(RE_DEF.findall(text))),
                "labels": sorted(set(x for x in RE_LABEL.findall(text)
                                     if x not in KEYWORDS and not x.isupper())),
                "funcs": ufuncs,
                "pragmas": dict(prag.most_common()),
                "pragma_lines": prag_lines,
                "types": {t: text.count(t) for t in TYPES if text.count(t)},
            })

out = {"groups": GROUPS, "files": files,
       "total_files": len(files),
       "total_lines": sum(f["lines"] for f in files)}
json.dump(out, open("inventory.json", "w"), indent=1)
print(f"files {out['total_files']}  lines {out['total_lines']}")
print(f"{'file':<46}{'lines':>7}{'funcs':>7}{'pragma':>8}{'tmpl':>6}{'cls':>5}")
for f in files:
    print(f"{f['rel']:<46}{f['lines']:>7}{len(f['funcs']):>7}"
          f"{sum(f['pragmas'].values()):>8}{f['templates']:>6}{len(f['classes']):>5}")
