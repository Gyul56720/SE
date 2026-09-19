# -*- coding: utf-8 -*-
"""Deep extractor: full class bodies, full signatures, vendor headers."""
import json, os, re, collections

ROOT="/home/user/hls_study"
CORPUS=["Vitis_solver","Vitis_solver_L2","Vitis_security","Vitis_dsp_fft","finn_hlslib"]
VENDOR=os.path.join(ROOT,"vendor")
KW={"if","for","while","switch","return","sizeof","catch","do","else","defined"}

def strip_comments(s):
    s=re.sub(r'/\*.*?\*/', lambda m:"\n"*m.group().count("\n"), s, flags=re.S)
    return re.sub(r'//[^\n]*', '', s)

def balanced(text, i, o='{', c='}'):
    d=0
    while i<len(text):
        if text[i]==o: d+=1
        elif text[i]==c:
            d-=1
            if d==0: return i
        i+=1
    return -1

def tmpl_before(text, pos):
    """template<...> immediately preceding pos."""
    head=text[max(0,pos-1400):pos]
    m=None
    for mm in re.finditer(r'template\s*<', head): m=mm
    if not m: return ""
    i=head.index('<', m.start())
    d=0
    for j in range(i,len(head)):
        if head[j]=='<': d+=1
        elif head[j]=='>':
            d-=1
            if d==0:
                tail=head[j+1:].strip()
                if tail and not re.match(r'^(class|struct|typename|inline|static|constexpr|[\w:<>,\s\*&]+$)', tail):
                    return ""
                return " ".join(head[m.start():j+1].split())
    return ""

CLS=re.compile(r'\b(class|struct)\s+([A-Za-z_]\w*)\s*(<[^{;]*?>)?\s*(:[^{;]*?)?\{')
def classes_of(text):
    out=[]
    for m in CLS.finditer(text):
        end=balanced(text, text.index('{', m.end()-1))
        if end<0: continue
        body=text[text.index('{', m.end()-1)+1:end]
        ln=text[:m.start()].count("\n")+1
        # members
        tds=[" ".join(x.split()) for x in re.findall(r'\btypedef\s+[^;]{1,120};', body)]
        sts=[" ".join(x.split()) for x in re.findall(r'\bstatic\s+(?:const|constexpr)\s+[^;]{1,120};', body)]
        fns=[]
        for fm in re.finditer(r'^[ \t]*((?:static\s+|inline\s+|virtual\s+|constexpr\s+|explicit\s+)*'
                              r'[A-Za-z_][\w:<>,\s\*&]*?)\s+([A-Za-z_]\w*)\s*\(([^;{)]{0,200})\)', body, re.M):
            if fm.group(2) in KW: continue
            fns.append((" ".join(fm.group(1).split()), fm.group(2),
                        " ".join(fm.group(3).split())[:150]))
        out.append({"kind":m.group(1),"name":m.group(2),"line":ln,
                    "spec":" ".join((m.group(3) or "").split())[:110],
                    "bases":" ".join((m.group(4) or "").split())[:110],
                    "tmpl":tmpl_before(text,m.start())[:230],
                    "typedefs":tds[:24],"statics":sts[:24],
                    "methods":fns[:30],"body_lines":body.count("\n")+1})
    return out

FN=re.compile(r'^[ \t]*((?:static\s+|inline\s+|constexpr\s+|extern\s+"C"\s+)*'
              r'[A-Za-z_][\w:<>,\s\*&]*?)\s+([A-Za-z_]\w*)\s*\(([^;{)]{0,300})\)\s*(?:const\s*)?\{', re.M)
def funcs_of(text):
    out=[]
    for m in FN.finditer(text):
        if m.group(2) in KW: continue
        ln=text[:m.start()].count("\n")+1
        out.append({"line":ln,"ret":" ".join(m.group(1).split())[:90],
                    "name":m.group(2),"params":" ".join(m.group(3).split())[:260],
                    "tmpl":tmpl_before(text,m.start())[:230]})
    seen=set(); u=[]
    for f in out:
        k=(f["name"],f["line"])
        if k in seen: continue
        seen.add(k); u.append(f)
    return u

def scan(path, rel, group):
    raw=open(path,encoding="utf-8",errors="replace").read()
    t=strip_comments(raw)
    return {"group":group,"rel":rel,"name":os.path.basename(path),
            "lines":raw.count("\n")+1,"bytes":len(raw),
            "classes":classes_of(t),"funcs":funcs_of(t),
            "includes":sorted(set(re.findall(r'#\s*include\s+[<"]([^>"]+)[>"]',raw))),
            "defines":sorted(set(re.findall(r'^\s*#\s*define\s+([A-Za-z_]\w*)',raw,re.M)))}

files=[]
for g in CORPUS:
    d=os.path.join(ROOT,g)
    for dp,_,ns in os.walk(d):
        for n in sorted(ns):
            p=os.path.join(dp,n)
            files.append(scan(p, os.path.relpath(p,ROOT), g))
vend=[]
for dp,_,ns in os.walk(VENDOR):
    for n in sorted(ns):
        p=os.path.join(dp,n)
        vend.append(scan(p, os.path.relpath(p,VENDOR), "vendor"))

out={"files":sorted(files,key=lambda f:f["rel"]),"vendor":sorted(vend,key=lambda f:f["rel"])}
json.dump(out, open("deep.json","w"), indent=1)
nc=sum(len(f["classes"]) for f in files); nf=sum(len(f["funcs"]) for f in files)
vc=sum(len(f["classes"]) for f in vend); vf=sum(len(f["funcs"]) for f in vend)
print(f"corpus: {len(files)} files, classes {nc}, funcs {nf}")
print(f"vendor: {len(vend)} files, {sum(f['lines'] for f in vend):,} lines, classes {vc}, funcs {vf}")
