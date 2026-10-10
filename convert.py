"""Convert the LaTeX Basilisk guide into pandoc-markdown pages for the
basilisk.fr sandbox (darcsit wiki).

usage: python convert.py SRC_DIR OUT_DIR PANDOC
"""
import os, re, subprocess, sys, shutil

SRC, OUT, PANDOC = sys.argv[1:4]
FIGDIR = os.path.join(OUT, "figures")
os.makedirs(FIGDIR, exist_ok=True)

main = open(os.path.join(SRC, "basilisk_guide.tex")).read()
preamble = main[:main.index(r"\title{")]
macros = "\n".join(l for l in preamble.splitlines() if l.startswith(r"\newcommand"))
order = [c for c in re.findall(r"\\input\{chapters/(\w+)\}", main) if c != "B_case_study"]

# ---------- balanced-brace helpers ----------
def group(s, i):
    """s[i] == '{' -> (content, index after closing brace)"""
    assert s[i] == "{", s[i:i+20]
    d = 0
    for j in range(i, len(s)):
        if s[j] == "{" and s[j-1] != "\\": d += 1
        elif s[j] == "}" and s[j-1] != "\\":
            d -= 1
            if d == 0: return s[i+1:j], j+1
    raise ValueError("unbalanced")

def sub_cmd(s, name, fn):
    """replace \\name{arg} (balanced) by fn(arg)"""
    out, i = [], 0
    pat = re.compile(r"\\" + name + r"(?![a-zA-Z])\s*")
    while True:
        m = pat.search(s, i)
        if not m: out.append(s[i:]); return "".join(out)
        if m.end() >= len(s) or s[m.end()] != "{":
            out.append(s[i:m.end()]); i = m.end(); continue
        arg, j = group(s, m.end())
        out.append(s[i:m.start()]); out.append(fn(arg)); i = j

# ---------- labels from the .aux file ----------
aux = open(os.path.join(SRC, "basilisk_guide.aux")).read()
labels = {}  # label -> (kind, number)
for m in re.finditer(r"\\newlabel\{([^}]*)@cref\}\{\{\[(\w+)\]\[[^]]*\]\[[^]]*\]([^}]*)\}", aux):
    labels[m.group(1)] = (m.group(2), m.group(3))

# chapter number / page name per file, and which page holds each label
chapnum, page, label_page = {}, {}, {}
for stem in order:
    tex = open(os.path.join(SRC, "chapters", stem + ".tex")).read()
    lab = re.search(r"\\chapter\{.*?\}\s*\\label\{([^}]*)\}", tex, re.S)
    num = labels[lab.group(1)][1] if lab else stem[0]
    chapnum[stem] = num
    short = re.sub(r"^[A-Z]?\d*_", "", stem)
    page[stem] = (f"{int(num):02d}" if num.isdigit() else num) + "_" + short
    for l in re.findall(r"\\label\{([^}]*)\}", tex):
        label_page[l] = page[stem]

KIND = {"chapter": "chapter", "section": "section", "subsection": "section",
        "figure": "figure", "table": "table", "equation": "equation",
        "appendix": "appendix", "part": "part", "subfigure": "figure",
        "paragraph": "section", "align": "equation", "listing": "listing"}

def ref_text(lbl, kind_word=True):
    kind, num = labels.get(lbl, ("?", "??"))
    if kind in ("equation", "align"):
        txt = f"({num})"
        return txt if not kind_word else "equation " + txt
    if kind == "part":
        return f"part {num}"
    return (KIND.get(kind, kind) + " " + num) if kind_word else num

def make_ref(cur, cap):
    def f(arg):
        parts = []
        for lbl in [a.strip() for a in arg.split(",")]:
            txt = ref_text(lbl)
            if cap: txt = txt[0].upper() + txt[1:]
            cap_done = True
            pg = label_page.get(lbl)
            kind = labels.get(lbl, ("?",))[0]
            if pg is None or kind == "part":
                parts.append(txt)
            elif pg == cur:
                parts.append(txt if kind in ("equation", "align", "figure", "table")
                             else r"\href{#%s}{%s}" % (lbl, txt))
            else:
                anchor = "" if kind == "chapter" or kind in ("equation", "align", "figure", "table") else "#" + lbl
                parts.append(r"\href{%s%s}{%s}" % (pg, anchor, txt))
        return " and ".join(parts)
    return f

def eqref(cur):
    def f(lbl):
        txt = ref_text(lbl, kind_word=False)
        pg = label_page.get(lbl)
        return txt if pg in (None, cur) else r"\href{%s}{%s}" % (pg, txt)
    return f

bib = re.findall(r"\\bibitem\{(\w+)\}", main)
def cite(arg):
    return "[" + ", ".join(r"\href{references}{%d}" % (bib.index(k.strip()) + 1)
                           for k in arg.split(",")) + "]"

# ---------- figures -> PNG via pdflatex ----------
fig_tex = []   # standalone bodies, one per page
fig_names = []

def strip_top_caption(body):
    """remove the last \\caption{} that is not inside a subfigure; return (body, caption)"""
    cap = None
    depth_spans = [(m.start(), m.end()) for m in re.finditer(
        r"\\begin\{subfigure\}.*?\\end\{subfigure\}", body, re.S)]
    for m in reversed(list(re.finditer(r"\\caption(?![a-z])", body))):
        if any(a <= m.start() < b for a, b in depth_spans): continue
        cap, j = group(body, m.end())
        body = body[:m.start()] + body[j:]
        break
    return body, cap

def figures(tex, stem):
    def repl(m):
        body = m.group(1)
        lbl = re.search(r"\\label\{([^}]*)\}", body)
        lbl = lbl.group(1) if lbl else None
        body = re.sub(r"\\label\{[^}]*\}", "", body)
        body, cap = strip_top_caption(body)
        name = (lbl or f"{stem}_{len(fig_names)}").replace(":", "_")
        fig_names.append(name)
        body = sub_cmd(body, "Cref", lambda a: " and ".join(ref_text(x.strip()).capitalize() for x in a.split(",")))
        body = sub_cmd(body, "cref", lambda a: " and ".join(ref_text(x.strip()) for x in a.split(",")))
        fig_tex.append(body)
        num = labels.get(lbl, ("", ""))[1] if lbl else ""
        captxt = (f"Figure {num}: " if num else "") + (cap or "")
        return ("\n\\begin{figure}\\includegraphics{figures/%s.png}\\caption{%s}\\end{figure}\n"
                % (name, captxt))
    return re.sub(r"\\begin\{figure\}(?:\[[^]]*\])?(.*?)\\end\{figure\}", repl, tex, flags=re.S)

# ---------- boxes ----------
def boxes(tex):
    def incode(m):
        t = m.group(1)
        title = "In the code" + (": " + t if t else "")
        return "\\begin{quote}\n\\textbf{%s}\n\n%s\n\\end{quote}" % (title, m.group(2))
    tex = re.sub(r"\\begin\{incode\}(?:\[((?:[^][]|\[[^]]*\])*)\])?(.*?)\\end\{incode\}",
                 incode, tex, flags=re.S)
    def concept(m):
        return "\\begin{quote}\n\\textbf{%s}\n\n%s\n\\end{quote}" % (m.group(1), m.group(2))
    tex = re.sub(r"\\begin\{concept\}\{([^}]*)\}(.*?)\\end\{concept\}", concept, tex, flags=re.S)
    return tex

def tag_equations(tex):
    """put \\tag{n} before each \\label inside equation/align so MathJax numbers match the PDF"""
    def f(m):
        env = m.group(0)
        return re.sub(r"\\label\{([^}]*)\}",
                      lambda l: r"\tag{%s}\label{%s}" % (labels.get(l.group(1), ("", "?"))[1], l.group(1)),
                      env)
    return re.sub(r"\\begin\{(equation|align)\}.*?\\end\{\1\}", f, tex, flags=re.S)

def display(m):
    """$$\\begin{equation}..$$ -> plain $$..$$ with one \\tag, no \\label (MathJax/KaTeX safe)"""
    b = m.group(1)
    b = re.sub(r"\\label\{[^}]*\}", "", b)
    tags = re.findall(r"\\tag\{([^}]*)\}", b)
    b = re.sub(r"\\tag\{[^}]*\}", "", b)
    b = re.sub(r"\\(begin|end)\{equation\*?\}", "", b)
    b = re.sub(r"\\(begin|end)\{align\*?\}", r"\\\1{aligned}", b)
    b = b.strip()
    if tags:
        b += "\n\\tag{%s}" % (tags[0] if len(tags) == 1 else tags[0] + "--" + tags[-1])
    return "$$\n" + b + "\n$$"

# ---------- per chapter ----------
LUA = os.path.join(OUT, "..", "codeclass.lua")
open(LUA, "w").write(
    'function CodeBlock(b)\n'
    '  if b.classes[1] ~= "bash" then b.classes = {"literatec"} end\n'
    '  b.attributes = {} b.identifier = "" return b end\n'
    'function Div(d) return d.content end\n')

pages = []
for stem in order:
    cur = page[stem]
    tex = open(os.path.join(SRC, "chapters", stem + ".tex")).read()
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tex = re.sub(r"\\Cref\{app:case\}.*?\n\n", "", tex, flags=re.S)
    tex = figures(tex, stem)
    tex = boxes(tex)
    tex = tag_equations(tex)
    tex = sub_cmd(tex, "Cref", make_ref(cur, True))
    tex = sub_cmd(tex, "cref", make_ref(cur, False))
    tex = sub_cmd(tex, "eqref", eqref(cur))
    tex = sub_cmd(tex, "ref", lambda l: ref_text(l, False))
    tex = sub_cmd(tex, "cite", cite)
    tex = sub_cmd(tex, "paragraph", lambda a: r"\textbf{%s}" % a)
    # chapter=H1, section=H2, subsection=H3
    tex = re.sub(r"\\subsection(\*?)\{", r"\\subsubsection\1{", tex)
    tex = re.sub(r"\\section(\*?)\{", r"\\subsection\1{", tex)
    tex = tex.replace(r"\chapter{", r"\section{")
    num = chapnum[stem]
    tex = re.sub(r"\\section\{", r"\\section{%s " % (num if num.isdigit() else "Appendix " + num + ":"), tex, count=1)
    full = macros + "\n" + tex
    md = subprocess.run([PANDOC, "-f", "latex", "-t",
                         "markdown-raw_attribute-link_attributes"
                         "-simple_tables-multiline_tables-grid_tables-bracketed_spans-native_spans"
                         "-native_divs",
                         "--lua-filter", LUA, "--wrap=preserve"],
                        input=full, capture_output=True, text=True)
    if md.stderr.strip(): print(stem, md.stderr.strip()[:500], file=sys.stderr)
    out = md.stdout
    out = re.sub(r"^((?:> )?)``` ?\{?\.?(literatec|bash)\}?$", r"\1~~~\2", out, flags=re.M)
    out = re.sub(r"^((?:> )?)```$", r"\1~~~", out, flags=re.M)
    out = re.sub(r"\$\$(.*?)\$\$", display, out, flags=re.S)
    out = re.sub(r" \{#[^ }]* \.unnumbered\}$", "", out, flags=re.M)
    out = re.sub(r"^: (.*?) \{#([^}]*)\}$",
                 lambda m: ": Table %s: %s" % (labels.get(m.group(2), ("", "?"))[1], m.group(1)),
                 out, flags=re.S | re.M)
    open(os.path.join(OUT, cur), "w").write(out)
    pages.append((stem, cur))

# ---------- render figures ----------
style = preamble.replace(r"\documentclass[11pt,a4paper,oneside]{report}",
                         r"\documentclass[11pt,a4paper]{article}")
style = re.sub(r"\\usepackage\{fancyhdr\}", "", style)
style = re.sub(r"\\pagestyle\{fancy\}.*?\\setlength\{\\headheight\}\{[^}]*\}", "", style, flags=re.S)
doc = style + "\\pagestyle{empty}\n\\begin{document}\n"
for body in fig_tex:
    doc += "\\begin{figure}[H]\n%s\n\\end{figure}\n\\clearpage\n" % body
doc += "\\end{document}\n"
build = os.path.join(OUT, "..", "figbuild")
os.makedirs(build, exist_ok=True)
for d in ("data", "figures"):
    if not os.path.exists(os.path.join(build, d)):
        shutil.copytree(os.path.join(SRC, d), os.path.join(build, d))
open(os.path.join(build, "figs.tex"), "w").write(doc)
for _ in range(2):
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "figs.tex"], cwd=build,
                       capture_output=True, text=True)
if r.returncode: print(r.stdout[-3000:], file=sys.stderr)
subprocess.run(["pdfcrop", "--margins", "6", "figs.pdf", "crop.pdf"], cwd=build, capture_output=True)
subprocess.run(["pdftoppm", "-r", "200", "-png", "crop.pdf", "p"], cwd=build)
pngs = sorted(f for f in os.listdir(build) if f.startswith("p-") and f.endswith(".png"))
assert len(pngs) == len(fig_names), (len(pngs), len(fig_names))
for p, n in zip(pngs, fig_names):
    shutil.move(os.path.join(build, p), os.path.join(FIGDIR, n + ".png"))

import json
json.dump({"pages": pages, "chapnum": chapnum}, open(os.path.join(OUT, "..", "pages.json"), "w"))
print("pages", len(pages), "figures", len(fig_names))
