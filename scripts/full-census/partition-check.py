#!/usr/bin/env python3
"""phase-8 S3 · 顶层分区判据器（独立于两腿）。

裁定要求：判据器不得读两腿自产的 summary/stdout，一律从**原始行数据**重算。
输入只有四类原始件：
  1. 当前 golden manifest（analysis/golden/8.2.0-darwin-arm64-full.tsv）
  2. 主腿逐产物结果行  <ours stage>/ours-artifact-results.tsv
  3. 扩展腿逐产物结果行 <linkonly stage>/compare-artifacts.tsv
  4. 两腿各自的 identity/toolchains.json（身份证据，非结果摘要）

断言：
  ① 行分区：主腿 gate 行 + 扩展腿 link-only 行 = 43969，且与当前 golden 行集**不重不漏**
  ② 工程分区：1170 + 33 = 1203，不重不漏
  ③ 两腿所用 install 树身份一致，且等于当前活体 install 树
  ④（加强）两腿全部 gate 行 status 均为 MATCH——同样从原始行算，不采信腿的自述
"""
import csv, hashlib, json, sys
from pathlib import Path

REPO = Path("/Users/apple/Projects/openwch")
GOLDEN = REPO / "analysis/golden/8.2.0-darwin-arm64-full.tsv"
OURS_STAGE = REPO / "tmp/toolchain_8.2.0/evidence/s3/full-ours" / sys.argv[1]
LINK_STAGE = REPO / "tmp/toolchain_8.2.0/evidence/s4/linkonly-extension" / sys.argv[2]
INSTALL = REPO / "tmp/toolchain_8.2.0/work/darwin-x64/install/riscv-none-embed-gcc"

def read_tsv(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader((l for l in fh if not l.startswith("#")), delimiter="\t"))

fail = []
def check(name, cond, detail):
    print(f"{'PASS' if cond else 'FAIL'}  {name}: {detail}")
    if not cond:
        fail.append(name)

g = read_tsv(GOLDEN)
g_gate = {(r["index"], r["artifact"]) for r in g if r["class"] == "gate"}
g_link = {(r["index"], r["artifact"]) for r in g if r["class"] == "gate-link-only"}
g_all = {(r["index"], r["artifact"]) for r in g}
gp_gate = {r["index"] for r in g if r["class"] == "gate"}
gp_link = {r["index"] for r in g if r["class"] == "gate-link-only"}

main = read_tsv(OURS_STAGE / "ours-artifact-results.tsv")
link = read_tsv(LINK_STAGE / "compare-artifacts.tsv")
# Schema note (v2 fix): the class marker "gate-link-only" exists only in the
# golden manifest, which has to distinguish the two partitions in one file.
# Each leg tags its own rows "gate" within its own face, so the link leg's
# gate rows ARE the golden's gate-link-only partition.
m_gate = {(r["index"], r["artifact"]) for r in main if r["class"] == "gate"}
l_gate = {(r["index"], r["artifact"]) for r in link if r["class"] == "gate"}
mp = {r["index"] for r in main if r["class"] == "gate"}
lp = {r["index"] for r in link if r["class"] == "gate"}

# ---- ① 行分区 ----
check("row-counts", len(m_gate) == 42285 and len(l_gate) == 1684,
      f"main={len(m_gate)} link={len(l_gate)} sum={len(m_gate)+len(l_gate)}")
check("row-disjoint", not (m_gate & l_gate), f"overlap={len(m_gate & l_gate)}")
union = m_gate | l_gate
check("row-exhaustive-vs-golden", union == g_all,
      f"union={len(union)} golden={len(g_all)} missing={len(g_all-union)} extra={len(union-g_all)}")
check("row-partition-matches-golden-classes", m_gate == g_gate and l_gate == g_link,
      f"main==golden.gate:{m_gate == g_gate} link==golden.link:{l_gate == g_link}")

# ---- ② 工程分区 ----
check("project-counts", len(mp) == 1170 and len(lp) == 33,
      f"main={len(mp)} link={len(lp)} sum={len(mp)+len(lp)}")
check("project-disjoint", not (mp & lp), f"overlap={len(mp & lp)}")
check("project-exhaustive-vs-golden", (mp | lp) == (gp_gate | gp_link),
      f"union={len(mp|lp)} golden={len(gp_gate|gp_link)}")

# ---- ③ 两腿 install 树身份一致 ----
def ident(stage):
    # Schema note (v2 fix): d["ours"] is a MIXED mapping -- most values are
    # plain strings (root/side/compiler/target/dumpversion/arch/...), and only
    # the tool entries (gcc/as/ld/objcopy/objdump) are sub-dicts carrying
    # "sha256".  Select by shape rather than iterating everything.
    d = json.loads((stage / "identity/toolchains.json").read_text(encoding="utf-8"))
    tools = {k: v["sha256"] for k, v in d["ours"].items()
             if isinstance(v, dict) and "sha256" in v}
    return tools, d.get("ours_resolved")
mi, mr = ident(OURS_STAGE)
li, lr = ident(LINK_STAGE)
check("identity-non-empty", len(mi) >= 4 and set(mi) == set(li),
      f"main_tools={sorted(mi)} link_tools={sorted(li)}")
check("legs-same-toolchain", mi == li, f"main_gcc={mi.get('gcc','')[:16]} link_gcc={li.get('gcc','')[:16]}")
check("legs-same-install-path", mr == lr, f"{mr} vs {lr}")
live = {}
for name, rel in (("gcc", "bin/riscv-none-embed-gcc"), ("as", "bin/riscv-none-embed-as"),
                  ("ld", "bin/riscv-none-embed-ld"), ("objdump", "bin/riscv-none-embed-objdump")):
    p = INSTALL / rel
    live[name] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "ABSENT"
check("legs-match-live-install", all(mi.get(k) == v for k, v in live.items()),
      "; ".join(f"{k}:{'ok' if mi.get(k) == v else 'MISMATCH'}" for k, v in live.items()))

# ---- ④ 全部 gate 行 MATCH（从原始行算） ----
mbad = [r for r in main if r["class"] == "gate" and r["status"] != "MATCH"]
lbad = [r for r in link if r["class"] == "gate" and r["status"] != "MATCH"]
check("all-gate-rows-MATCH", not mbad and not lbad, f"main_bad={len(mbad)} link_bad={len(lbad)}")

print(f"\nPARTITION-{'PASS' if not fail else 'FAIL ' + ','.join(fail)}  total=43969")
sys.exit(1 if fail else 0)
