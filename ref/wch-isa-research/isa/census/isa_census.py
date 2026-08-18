#!/usr/bin/env python3
"""RISC-V instruction census over WCH-shipped binary libraries.

Pure static ISA-coverage counting from raw bytes. objdump is NOT trusted for the
main statistic: it refuses to decode WCH's private XW compressed extension when
.riscv.attributes is present (prints .2byte/.insn), and -- worse -- silently
decodes the very same halfwords as fld/fsd when the section is absent, because
it then falls back to a default ISA that includes D. Both failure modes are
cross-checked in `xcheck` mode instead.

Subcommands:
  selftest    assemble fixtures with the WCH GAS and verify the decoder
  control     positive control on .text.GetChipID
  scan        full census -> TSVs
  xcheck      objdump cross-reference for named archives
"""
import hashlib
import os
import re
import struct
import subprocess
import sys
from collections import Counter, OrderedDict

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
RESULTS = os.path.join(REPO, 'audit-report-f', 'followup', 'results')

AS = os.path.join(REPO, 'MRS_Toolchain_MAC_V240', 'Toolchain',
                  'RISC-V Embedded GCC12', 'bin', 'riscv-wch-elf-as')
OBJDUMP = os.path.join(REPO, 'MRS_Toolchain_MAC_V240', 'Toolchain',
                       'RISC-V Embedded GCC12', 'bin', 'riscv-wch-elf-objdump')
# Recorded, not used: the GCC15 objdump renders undecodable XW differently
# (".insn 2, 0x8008" instead of ".2byte 0x8008"), so any cross-check number
# is meaningless unless the generation is stated.
OBJDUMP15 = os.path.join(REPO, 'MRS_Toolchain_MAC_V240', 'Toolchain',
                         'RISC-V Embedded GCC15', 'bin', 'riscv32-wch-elf-objdump')
MARCH = 'rv32imac_zba_zbb_zbc_zbs_xw'

EVT_ROOT = os.path.join(REPO, 'tmp', 'wch-evt', 'evt')
MRS_ROOTS = [
    ('mrs24', os.path.join(REPO, 'MRS_Toolchain_MAC_V240', 'Toolchain')),
    ('mrs25', os.path.join(REPO, 'tmp', 'mrs-2.5', 'WCH', 'Toolchain')),
]
MRS_PATTERNS = (
    re.compile(r'^libIQ.*\.a$'),
    re.compile(r'^libprintf.*\.a$'),
    re.compile(r'^libsh.*lib\.a$'),   # covers libshflib.a as well
)


# --------------------------------------------------------------------------
# containers
# --------------------------------------------------------------------------
def ar_members(data):
    """Yield (name, bytes) for every ar member IN ORDER.

    Duplicate member names occur (e.g. libwchnet.a: 56 members / 28 unique
    names) and each carries its own code, so never key members by name.
    """
    if not data.startswith(b'!<arch>\n'):
        return
    off = 8
    longnames = b''
    while off + 60 <= len(data):
        hdr = data[off:off + 60]
        name = hdr[0:16].decode('latin1').rstrip()
        try:
            size = int(hdr[48:58].decode('latin1').strip())
        except ValueError:
            break
        body = data[off + 60:off + 60 + size]
        if name.startswith('//'):
            longnames = body
        elif name.startswith('/') and name[1:].isdigit():
            idx = int(name[1:])
            end = longnames.find(b'/\n', idx)
            if end < 0:
                end = longnames.find(b'\n', idx)
            yield longnames[idx:end].decode('latin1').rstrip('/'), body
        elif not name.startswith('/'):
            yield name.rstrip('/'), body
        off += 60 + size + (size & 1)


def elf_sections(elf):
    """Yield (name, sh_type, sh_flags, addr, bytes) for a 32-bit LE ELF."""
    if len(elf) < 52 or elf[:4] != b'\x7fELF' or elf[4] != 1 or elf[5] != 1:
        return
    e_shoff, = struct.unpack_from('<I', elf, 32)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('<HHH', elf, 46)
    if e_shoff == 0 or e_shnum == 0:
        return
    secs = []
    for i in range(e_shnum):
        o = e_shoff + i * e_shentsize
        if o + 40 > len(elf):
            return
        secs.append(struct.unpack_from('<IIIIII', elf, o))
    if e_shstrndx >= len(secs):
        return
    stroff, strsize = secs[e_shstrndx][4], secs[e_shstrndx][5]
    strtab = elf[stroff:stroff + strsize]
    for nm, typ, flags, addr, off, size in secs:
        end = strtab.find(b'\0', nm)
        name = strtab[nm:end].decode('latin1')
        yield name, typ, flags, addr, elf[off:off + size]


def exec_sections(elf):
    for name, typ, flags, addr, body in elf_sections(elf):
        if (flags & 0x4) and typ == 1 and body:   # SHF_EXECINSTR + PROGBITS
            yield name, addr, body


def elf_arch_string(elf):
    """Return the Tag_RISCV_arch string from .riscv.attributes, or ''."""
    for name, typ, flags, addr, body in elf_sections(elf):
        if name == '.riscv.attributes' and body:
            m = re.search(rb'rv(32|64)[a-z0-9_]*', body)
            if m:
                return m.group(0).decode('latin1')
            return '?'
    return ''


# --------------------------------------------------------------------------
# decoder
# --------------------------------------------------------------------------
UNK = ('unknown', None)

# XW (xw2p2) occupies these RVC slots. Verified against GAS -march=*_xw:
#   Q0 f3=1 -> c.lbu   (standard c.fld slot)
#   Q0 f3=5 -> c.sb    (standard c.fsd slot)
#   Q0 f3=4 -> c.lbusp/c.lhusp/c.sbsp/c.shsp, discriminated by bits[6:5]
#              (standard RVC "reserved" slot; missing this group undercounts
#               XW badly because every sp-relative byte/half access lives here)
#   Q2 f3=1 -> c.lhu   (standard c.fldsp slot)
#   Q2 f3=5 -> c.sh    (standard c.fsdsp slot)
XW_Q0F4 = ('c.lbusp', 'c.lhusp', 'c.sbsp', 'c.shsp')

_C1_F4_ALU = {0: 'c.sub', 1: 'c.xor', 2: 'c.or', 3: 'c.and'}


def dec16(h):
    q = h & 3
    f3 = (h >> 13) & 7
    if q == 0:
        if f3 == 1:
            return ('XW', 'c.lbu')
        if f3 == 4:
            return ('XW', XW_Q0F4[(h >> 5) & 3])
        if f3 == 5:
            return ('XW', 'c.sb')
        if f3 == 0:
            # nzuimm == 0 (incl. the all-zero halfword) is a defined illegal
            # encoding -- keep it in `unknown`, it marks data/padding.
            return ('RVC-std', 'c.addi4spn') if (h >> 5) & 0xFF else UNK
        if f3 == 2:
            return ('RVC-std', 'c.lw')
        if f3 == 6:
            return ('RVC-std', 'c.sw')
        return ('RVC-F', 'c.flw' if f3 == 3 else 'c.fsw')
    if q == 1:
        if f3 == 0:
            # C.NOP is exactly rd==0 && imm==0; rd==0 with a nonzero immediate
            # is a HINT, still a C.ADDI encoding.
            return ('RVC-std', 'c.nop' if (h & 0x1FFC) == 0 else 'c.addi')
        if f3 == 1:
            return ('RVC-std', 'c.jal')
        if f3 == 2:
            return ('RVC-std', 'c.li')
        if f3 == 3:
            return ('RVC-std', 'c.addi16sp' if ((h >> 7) & 0x1F) == 2 else 'c.lui')
        if f3 == 4:
            sub = (h >> 10) & 3
            if sub == 0:
                return ('RVC-std', 'c.srli')
            if sub == 1:
                return ('RVC-std', 'c.srai')
            if sub == 2:
                return ('RVC-std', 'c.andi')
            if (h >> 12) & 1:
                return UNK          # c.subw/c.addw are RV64-only
            return ('RVC-std', _C1_F4_ALU[(h >> 5) & 3])
        if f3 == 5:
            return ('RVC-std', 'c.j')
        return ('RVC-std', 'c.beqz' if f3 == 6 else 'c.bnez')
    # q == 2
    if f3 == 1:
        return ('XW', 'c.lhu')
    if f3 == 5:
        return ('XW', 'c.sh')
    if f3 == 0:
        return ('RVC-std', 'c.slli')
    if f3 == 2:
        return ('RVC-std', 'c.lwsp') if ((h >> 7) & 0x1F) else UNK
    if f3 == 3:
        return ('RVC-F', 'c.flwsp')
    if f3 == 6:
        return ('RVC-std', 'c.swsp')
    if f3 == 7:
        return ('RVC-F', 'c.fswsp')
    # f3 == 4
    rd, rs2, top = (h >> 7) & 0x1F, (h >> 2) & 0x1F, (h >> 12) & 1
    if not top:
        if rs2 == 0:
            return ('RVC-std', 'c.jr') if rd else UNK
        return ('RVC-std', 'c.mv')
    if rs2 == 0:
        return ('RVC-std', 'c.ebreak' if rd == 0 else 'c.jalr')
    return ('RVC-std', 'c.add')


_BRANCH = {0: 'beq', 1: 'bne', 4: 'blt', 5: 'bge', 6: 'bltu', 7: 'bgeu'}
_LOAD = {0: 'lb', 1: 'lh', 2: 'lw', 4: 'lbu', 5: 'lhu'}
_STORE = {0: 'sb', 1: 'sh', 2: 'sw'}
_OPIMM = {0: 'addi', 2: 'slti', 3: 'sltiu', 4: 'xori', 6: 'ori', 7: 'andi'}
_OP0 = {0: 'add', 1: 'sll', 2: 'slt', 3: 'sltu', 4: 'xor', 5: 'srl', 6: 'or', 7: 'and'}
_MULDIV = {0: 'mul', 1: 'mulh', 2: 'mulhsu', 3: 'mulhu',
           4: 'div', 5: 'divu', 6: 'rem', 7: 'remu'}
_ZBB_UNARY = {0: 'clz', 1: 'ctz', 2: 'cpop', 4: 'sext.b', 5: 'sext.h'}
_ZBB_MINMAX = {4: 'min', 5: 'minu', 6: 'max', 7: 'maxu'}
_ZBC = {1: 'clmul', 2: 'clmulr', 3: 'clmulh'}
_ZBA = {2: 'sh1add', 4: 'sh2add', 6: 'sh3add'}
_CSR = {1: 'csrrw', 2: 'csrrs', 3: 'csrrc', 5: 'csrrwi', 6: 'csrrsi', 7: 'csrrci'}
_PRIV = {0x000: 'ecall', 0x001: 'ebreak', 0x002: 'uret', 0x102: 'sret',
         0x105: 'wfi', 0x302: 'mret', 0x7b2: 'dret', 0x104: 'sfence.vm'}
_AMO = {0: 'amoadd', 1: 'amoswap', 2: 'lr', 3: 'sc', 4: 'amoxor', 8: 'amoor',
        12: 'amoand', 16: 'amomin', 20: 'amomax', 24: 'amominu', 28: 'amomaxu'}
_FMA = {0x43: 'fmadd', 0x47: 'fmsub', 0x4b: 'fnmsub', 0x4f: 'fnmadd'}
_OPFP = {0x00: 'fadd', 0x04: 'fsub', 0x08: 'fmul', 0x0c: 'fdiv', 0x2c: 'fsqrt'}
_FSGNJ = {0: 'fsgnj', 1: 'fsgnjn', 2: 'fsgnjx'}
_FCMP = {0: 'fle', 1: 'flt', 2: 'feq'}
_CUSTOM = {0x0b: 'custom0', 0x2b: 'custom1', 0x5b: 'custom2', 0x7b: 'custom3'}


def _opfp(w, f3, f7, rs2):
    fmt = f7 & 3
    sfx = {0: '.s', 1: '.d', 2: '.h', 3: '.q'}[fmt]
    cat = {0: 'RVF', 1: 'RVD', 2: 'RVF', 3: 'RVD'}[fmt]
    base = f7 & ~3
    if base in _OPFP:
        return (cat, _OPFP[base] + sfx)
    if base == 0x10:
        return (cat, _FSGNJ[f3] + sfx) if f3 in _FSGNJ else UNK
    if base == 0x14:
        return (cat, ('fmin' if f3 == 0 else 'fmax') + sfx) if f3 < 2 else UNK
    if base == 0x50:
        return (cat, _FCMP[f3] + sfx) if f3 in _FCMP else UNK
    if base == 0x20:
        return (cat, 'fcvt' + sfx + {0: '.s', 1: '.d', 2: '.h', 3: '.q'}[rs2 & 3])
    if base == 0x60:
        return (cat, 'fcvt.w%s%s' % ('u' if rs2 & 1 else '', sfx))
    if base == 0x68:
        return (cat, 'fcvt%s.w%s' % (sfx, 'u' if rs2 & 1 else ''))
    if base == 0x70:
        return (cat, ('fmv.x.w' if fmt == 0 else 'fmv.x.d') if f3 == 0
                else 'fclass' + sfx)
    if base == 0x78:
        return (cat, 'fmv.w.x' if fmt == 0 else 'fmv.d.x')
    return UNK


def dec32(w):
    op = w & 0x7F
    f3 = (w >> 12) & 7
    f7 = (w >> 25) & 0x7F
    rs2 = (w >> 20) & 0x1F
    imm12 = (w >> 20) & 0xFFF

    if op == 0x37:
        return ('RVI', 'lui')
    if op == 0x17:
        return ('RVI', 'auipc')
    if op == 0x6F:
        return ('RVI', 'jal')
    if op == 0x67:
        return ('RVI', 'jalr') if f3 == 0 else UNK
    if op == 0x63:
        return ('RVI', _BRANCH[f3]) if f3 in _BRANCH else UNK
    if op == 0x03:
        return ('RVI', _LOAD[f3]) if f3 in _LOAD else UNK
    if op == 0x23:
        return ('RVI', _STORE[f3]) if f3 in _STORE else UNK

    if op == 0x13:
        if f3 in _OPIMM:
            return ('RVI', _OPIMM[f3])
        if f3 == 1:
            if f7 == 0x00:
                return ('RVI', 'slli')
            if f7 == 0x30:
                return ('Zbb', _ZBB_UNARY[rs2]) if rs2 in _ZBB_UNARY else UNK
            if f7 == 0x14:
                return ('Zbs', 'bseti')
            if f7 == 0x24:
                return ('Zbs', 'bclri')
            if f7 == 0x34:
                return ('Zbs', 'binvi')
            return UNK
        if f3 == 5:
            if f7 == 0x00:
                return ('RVI', 'srli')
            if f7 == 0x20:
                return ('RVI', 'srai')
            if f7 == 0x30:
                return ('Zbb', 'rori')
            if f7 == 0x24:
                return ('Zbs', 'bexti')
            if f7 == 0x14 and rs2 == 7:
                return ('Zbb', 'orc.b')
            if f7 == 0x34 and rs2 == 0x18:
                return ('Zbb', 'rev8')
            return UNK
        return UNK

    if op == 0x33:
        if f7 == 0x00:
            return ('RVI', _OP0[f3])
        if f7 == 0x01:
            return ('RVM', _MULDIV[f3])
        if f7 == 0x20:
            if f3 == 0:
                return ('RVI', 'sub')
            if f3 == 5:
                return ('RVI', 'sra')
            if f3 == 4:
                return ('Zbb', 'xnor')
            if f3 == 6:
                return ('Zbb', 'orn')
            if f3 == 7:
                return ('Zbb', 'andn')
            return UNK
        if f7 == 0x05:
            if f3 in _ZBC:
                return ('Zbc', _ZBC[f3])
            if f3 in _ZBB_MINMAX:
                return ('Zbb', _ZBB_MINMAX[f3])
            return UNK
        if f7 == 0x10:
            return ('Zba', _ZBA[f3]) if f3 in _ZBA else UNK
        if f7 == 0x04 and f3 == 4 and rs2 == 0:
            return ('Zbb', 'zext.h')
        if f7 == 0x14 and f3 == 1:
            return ('Zbs', 'bset')
        if f7 == 0x24:
            if f3 == 1:
                return ('Zbs', 'bclr')
            if f3 == 5:
                return ('Zbs', 'bext')
            return UNK
        if f7 == 0x34 and f3 == 1:
            return ('Zbs', 'binv')
        if f7 == 0x30:
            if f3 == 1:
                return ('Zbb', 'rol')
            if f3 == 5:
                return ('Zbb', 'ror')
            return UNK
        return UNK

    if op == 0x0F:
        # MISC-MEM. WCH parks its 32-bit block-move instruction at f3=7 here;
        # objdump (both generations) decodes it, so the mnemonic is confirmed.
        if f3 == 0:
            return ('system', 'fence.tso' if (w >> 28) == 8 else 'fence')
        if f3 == 1:
            return ('system', 'fence.i')
        if f3 == 7:
            return ('custom-32', 'mcpy')
        return ('custom-32', 'custom0x0f:f3=%d' % f3)

    if op == 0x73:
        if f3 == 0:
            return ('system', _PRIV[imm12]) if imm12 in _PRIV else UNK
        return ('Zicsr', _CSR[f3]) if f3 in _CSR else UNK

    if op == 0x2F:
        f5 = (w >> 27) & 0x1F
        if f5 not in _AMO or f3 not in (2, 3):
            return UNK
        return ('RVA', _AMO[f5] + ('.w' if f3 == 2 else '.d'))

    if op == 0x07:
        if f3 == 2:
            return ('RVF', 'flw')
        if f3 == 3:
            return ('RVD', 'fld')
        return UNK
    if op == 0x27:
        if f3 == 2:
            return ('RVF', 'fsw')
        if f3 == 3:
            return ('RVD', 'fsd')
        return UNK
    if op in _FMA:
        fmt = (w >> 25) & 3
        if fmt > 1:
            return UNK
        return ('RVF' if fmt == 0 else 'RVD',
                _FMA[op] + ('.s' if fmt == 0 else '.d'))
    if op == 0x53:
        return _opfp(w, f3, f7, rs2)

    if op in _CUSTOM:
        # No mnemonic is knowable from the encoding alone -> emit the
        # encoding signature rather than guessing a name.
        return ('custom-32', '%s:f3=%d,f7=0x%02x' % (_CUSTOM[op], f3, f7))
    return UNK


_C16 = {}
_C32 = {}


def d16(h):
    r = _C16.get(h)
    if r is None:
        r = _C16[h] = dec16(h)
    return r


def d32(w):
    r = _C32.get(w)
    if r is None:
        r = _C32[w] = dec32(w)
    return r


def feat16(h):
    return 'q=%d,f3=%d,b65=%d' % (h & 3, (h >> 13) & 7, (h >> 5) & 3)


def feat32(w):
    return 'op=0x%02x,f3=%d,f7=0x%02x,rs2=%d' % (
        w & 0x7F, (w >> 12) & 7, (w >> 25) & 0x7F, (w >> 20) & 0x1F)


def scan(code):
    """Linear sweep. Yields (category, mnemonic_or_sig, length, raw, offset)."""
    i, L = 0, len(code)
    while i + 1 < L:
        h = code[i] | (code[i + 1] << 8)
        if (h & 3) != 3:
            cat, mn = d16(h)
            yield cat, (mn or feat16(h)), 2, h, i
            i += 2
            continue
        if (h & 0x1F) == 0x1F:
            # 48-bit or wider encoding: advance conservatively by 2 and
            # book it as unknown rather than pretending to know the length.
            yield 'unknown', 'wide:len5=0x%02x' % (h & 0x1F), 2, h, i
            i += 2
            continue
        if i + 4 > L:
            yield 'unknown', 'truncated', L - i, h, i
            break
        w = struct.unpack_from('<I', code, i)[0]
        cat, mn = d32(w)
        yield cat, (mn or feat32(w)), 4, w, i
        i += 4


# --------------------------------------------------------------------------
# inventory
# --------------------------------------------------------------------------
def collect_inputs():
    """Return scope -> list of absolute archive paths (spaces safe: os.walk)."""
    out = OrderedDict()
    evt = []
    for root, _dirs, files in os.walk(EVT_ROOT):
        for f in files:
            if f.endswith('.a'):
                evt.append(os.path.join(root, f))
    out['evt'] = sorted(evt)
    for scope, base in MRS_ROOTS:
        acc = []
        for root, _dirs, files in os.walk(base):
            for f in files:
                if any(p.match(f) for p in MRS_PATTERNS):
                    acc.append(os.path.join(root, f))
        out[scope] = sorted(acc)
    return out


def dedup(paths):
    """Group by sha256. Returns list of (rep_path, [all_paths], sha256_hex)."""
    groups = OrderedDict()
    for p in paths:
        try:
            with open(p, 'rb') as fh:
                h = hashlib.sha256(fh.read()).hexdigest()
        except OSError as e:
            print('ERROR unreadable: %s: %s' % (p, e), file=sys.stderr)
            raise SystemExit(2)
        groups.setdefault(h, []).append(p)
    return [(g[0], g, h) for h, g in groups.items()]


def sha256_file(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _first_line(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return (r.stdout or r.stderr).splitlines()[0].strip()
    except (OSError, IndexError) as e:
        return 'UNAVAILABLE (%s)' % e


def provenance():
    """Everything a third party needs to re-run this census identically."""
    import datetime
    return OrderedDict([
        ('date', datetime.date.today().isoformat()),
        ('repo', REPO),
        ('script', os.path.relpath(os.path.abspath(__file__), REPO)),
        ('script_sha256', sha256_file(os.path.abspath(__file__))),
        ('python', _first_line([sys.executable, '--version'])),
        ('python_exe', sys.executable),
        ('assembler', os.path.relpath(AS, REPO)),
        ('assembler_version', _first_line([AS, '--version'])),
        ('assembler_march', MARCH),
        ('objdump_xcheck', os.path.relpath(OBJDUMP, REPO)),
        ('objdump_xcheck_ver', _first_line([OBJDUMP, '--version'])),
        ('objdump_gcc15', os.path.relpath(OBJDUMP15, REPO)),
        ('objdump_gcc15_ver', _first_line([OBJDUMP15, '--version'])),
    ])


# --------------------------------------------------------------------------
# self-tests
# --------------------------------------------------------------------------
RVC_FIXTURE = """
	c.nop
	c.addi4spn a0, sp, 8
	c.lw    a0, 4(a1)
	c.sw    a0, 8(a1)
	c.addi  a0, 1
	c.jal   .
	c.li    a0, 5
	c.lui   a0, 1
	c.addi16sp sp, 32
	c.srli  a0, 3
	c.srai  a0, 3
	c.andi  a0, 7
	c.sub   a0, a1
	c.xor   a0, a1
	c.or    a0, a1
	c.and   a0, a1
	c.j     .
	c.beqz  a0, .
	c.bnez  a0, .
	c.slli  a0, 3
	c.lwsp  a0, 4(sp)
	c.jr    ra
	c.mv    a0, a1
	c.jalr  ra
	c.add   a0, a1
	c.swsp  a0, 4(sp)
	c.ebreak
"""

RV32_FIXTURE = """
	lui     a0, 1
	auipc   a0, 1
	jal     ra, .
	jalr    ra, 0(a0)
	beq     a0, a1, .
	bne     a0, a1, .
	blt     a0, a1, .
	bgeu    a0, a1, .
	lb      a0, 0(a1)
	lh      a0, 0(a1)
	lw      a0, 0(a1)
	lbu     a0, 0(a1)
	lhu     a0, 0(a1)
	sb      a0, 0(a1)
	sh      a0, 0(a1)
	sw      a0, 0(a1)
	addi    a0, a1, 1
	slti    a0, a1, 1
	sltiu   a0, a1, 1
	xori    a0, a1, 1
	ori     a0, a1, 1
	andi    a0, a1, 1
	slli    a0, a1, 3
	srli    a0, a1, 3
	srai    a0, a1, 3
	add     a0, a1, a2
	sub     a0, a1, a2
	sll     a0, a1, a2
	slt     a0, a1, a2
	sltu    a0, a1, a2
	xor     a0, a1, a2
	srl     a0, a1, a2
	sra     a0, a1, a2
	or      a0, a1, a2
	and     a0, a1, a2
	fence
	fence.i
	ecall
	ebreak
	mret
	wfi
	csrrw   a0, mstatus, a1
	csrrs   a0, mstatus, a1
	csrrc   a0, mstatus, a1
	csrrwi  a0, mstatus, 3
	csrrsi  a0, mstatus, 3
	csrrci  a0, mstatus, 3
	mul     a0, a1, a2
	mulh    a0, a1, a2
	mulhsu  a0, a1, a2
	mulhu   a0, a1, a2
	div     a0, a1, a2
	divu    a0, a1, a2
	rem     a0, a1, a2
	remu    a0, a1, a2
	lr.w    a0, (a1)
	sc.w    a0, a1, (a2)
	amoswap.w a0, a1, (a2)
	amoadd.w  a0, a1, (a2)
	amoxor.w  a0, a1, (a2)
	amoand.w  a0, a1, (a2)
	amoor.w   a0, a1, (a2)
	amomin.w  a0, a1, (a2)
	amomaxu.w a0, a1, (a2)
	sh1add  a0, a1, a2
	sh2add  a0, a1, a2
	sh3add  a0, a1, a2
	andn    a0, a1, a2
	orn     a0, a1, a2
	xnor    a0, a1, a2
	clz     a0, a1
	ctz     a0, a1
	cpop    a0, a1
	sext.b  a0, a1
	sext.h  a0, a1
	zext.h  a0, a1
	min     a0, a1, a2
	minu    a0, a1, a2
	max     a0, a1, a2
	maxu    a0, a1, a2
	rol     a0, a1, a2
	ror     a0, a1, a2
	rori    a0, a1, 3
	orc.b   a0, a1
	rev8    a0, a1
	clmul   a0, a1, a2
	clmulh  a0, a1, a2
	clmulr  a0, a1, a2
	bclr    a0, a1, a2
	bclri   a0, a1, 3
	bext    a0, a1, a2
	bexti   a0, a1, 3
	binv    a0, a1, a2
	binvi   a0, a1, 3
	bset    a0, a1, a2
	bseti   a0, a1, 3
	mcpy    a0, a1, a2
"""

XW_FIXTURE = """
	c.lbu   a0, 0(a1)
	c.lbu   a0, 3(a1)
	c.lhu   a0, 0(a1)
	c.lhu   a0, 2(a1)
	c.sb    a0, 0(a1)
	c.sb    a0, 3(a1)
	c.sh    a0, 0(a1)
	c.sh    a0, 2(a1)
	c.lbusp a0, 0(sp)
	c.lbusp a0, 5(sp)
	c.lhusp a0, 0(sp)
	c.lhusp a0, 6(sp)
	c.sbsp  a0, 0(sp)
	c.sbsp  a0, 5(sp)
	c.shsp  a0, 0(sp)
	c.shsp  a0, 6(sp)
"""


def _assemble(src, tmpdir, tag, norvc=False):
    body = '\t.option norelax\n' + ('\t.option norvc\n' if norvc else '') + src
    s = os.path.join(tmpdir, tag + '.s')
    o = os.path.join(tmpdir, tag + '.o')
    with open(s, 'w') as fh:
        fh.write('\t.text\n' + body + '\n')
    r = subprocess.run([AS, '-march=' + MARCH, '-mabi=ilp32', '-o', o, s],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('assembler failed for %s:\n%s' % (tag, r.stderr))
    with open(o, 'rb') as fh:
        elf = fh.read()
    for _n, _a, code in exec_sections(elf):
        return code
    raise SystemExit('no exec section in %s' % tag)


def selftest(tmpdir):
    ok = True
    for tag, src, norvc in (('rvc', RVC_FIXTURE, False),
                            ('rv32', RV32_FIXTURE, True),
                            ('xw', XW_FIXTURE, False)):
        expect = [ln.split()[0] for ln in src.strip().splitlines() if ln.strip()]
        code = _assemble(src, tmpdir, tag, norvc)
        got = [(m, c, raw, ln) for c, m, ln, raw, _o in scan(code)]
        if len(got) != len(expect):
            print('FAIL %s: %d decoded vs %d expected' % (tag, len(got), len(expect)))
            ok = False
        for exp, (mn, cat, raw, ln) in zip(expect, got):
            if exp != mn:
                print('FAIL %s: expected %-10s got %-10s [%s] raw=0x%0*x'
                      % (tag, exp, mn, cat, ln * 2, raw))
                ok = False
        print('%-5s %3d insns, %s' % (tag, len(got), 'OK' if ok else 'see above'))
    return ok


# --------------------------------------------------------------------------
# XW 1.0 vs 2.2 encoding differential
# --------------------------------------------------------------------------
# The bundled GAS only knows ONE XW opcode table: -march=..._xw{1p0,2p0,2p2,3p0}
# all assemble byte-identically and the version string is a pure attribute
# passthrough (xw3p0 is accepted too, and it does not exist).  Its default is
# xw1p0.  Every XW-declaring archive in the corpus says xw2p2.  So a fixture
# built from this assembler can only ever cover the 1.0 encoding set, and any
# 2.2-only encoding point would silently be decoded under 1.0 semantics.
# `xwdiff` closes that hole empirically: enumerate everything GAS can emit,
# then subtract it from what the xw2p2 archives actually contain.
XW_ASM_MARCH = 'rv32imac_xw1p0'
XW_MNEMONICS = ('c.lbu', 'c.lhu', 'c.sb', 'c.sh',
                'c.lbusp', 'c.lhusp', 'c.sbsp', 'c.shsp')
XW_SP_FORMS = ('c.lbusp', 'c.lhusp', 'c.sbsp', 'c.shsp')


def in_xw_slot(h):
    """True if the halfword falls in a slot this census attributes to XW."""
    q, f3 = h & 3, (h >> 13) & 7
    return (q == 0 and f3 in (1, 4, 5)) or (q == 2 and f3 in (1, 5))


_ERRLINE = re.compile(r':(\d+): Error')


def _assemble_tolerant(lines, tmpdir, tag, march):
    """Assemble one instruction per line, dropping whatever GAS rejects.

    Returns (kept_lines, code_bytes). Iterates because GAS stops reporting
    after enough errors on some inputs.
    """
    s = os.path.join(tmpdir, tag + '.s')
    o = os.path.join(tmpdir, tag + '.o')
    kept = list(lines)
    for _ in range(40):
        with open(s, 'w') as fh:
            fh.write('\t.text\n\t.option norelax\n')
            fh.write(''.join('\t%s\n' % l for l in kept))
        r = subprocess.run([AS, '-march=' + march, '-mabi=ilp32', '-o', o, s],
                           capture_output=True, text=True)
        if r.returncode == 0:
            with open(o, 'rb') as fh:
                elf = fh.read()
            for _n, _a, code in exec_sections(elf):
                return kept, code
            return kept, b''
        bad = {int(m.group(1)) for m in _ERRLINE.finditer(r.stderr)}
        if not bad:
            raise SystemExit('assembler failed with no parseable error:\n'
                             + r.stderr[:2000])
        # source line N corresponds to kept[N - 3] (2 header lines, 1-based)
        drop = {n - 3 for n in bad}
        kept = [l for i, l in enumerate(kept) if i not in drop]
        if not kept:
            return [], b''
    raise SystemExit('assembler did not converge for %s' % tag)


def enumerate_xw_asm(tmpdir):
    """Every XW encoding this assembler can emit. Returns {enc: [asm, ...]}."""
    regs = ['x%d' % i for i in range(32)]
    imms = list(range(-72, 264))
    # pass 1: which registers are legal (immediate 0)
    cand = []
    for mn in XW_MNEMONICS:
        for rd in regs:
            if mn in XW_SP_FORMS:
                cand.append('%s %s, 0(sp)' % (mn, rd))
            else:
                for rs1 in regs:
                    cand.append('%s %s, 0(%s)' % (mn, rd, rs1))
    ok1, _code = _assemble_tolerant(cand, tmpdir, 'xwregs', XW_ASM_MARCH)
    legal = {}
    for line in ok1:
        mn, rest = line.split(' ', 1)
        legal.setdefault(mn, []).append(rest)
    # pass 2: full cross product of legal register pairs x candidate immediates
    cand = []
    for mn, forms in legal.items():
        for form in forms:
            head = form.split(',')[0].strip()
            base = form.split('(')[1].rstrip(')')
            for im in imms:
                cand.append('%s %s, %d(%s)' % (mn, head, im, base))
    ok2, code = _assemble_tolerant(cand, tmpdir, 'xwfull', XW_ASM_MARCH)
    if len(code) != 2 * len(ok2):
        raise SystemExit('XW fixture produced non-16-bit output: %d bytes / %d '
                         'insns' % (len(code), len(ok2)))
    out = {}
    for i, line in enumerate(ok2):
        enc = code[2 * i] | (code[2 * i + 1] << 8)
        out.setdefault(enc, []).append(line)
    return out, legal


def archive_xw_version(path):
    """Declared XW version across an archive's members: 'xw2p2', '' or 'mixed'."""
    with open(path, 'rb') as fh:
        data = fh.read()
    seen = set()
    for _mn, body in ar_members(data):
        if not body.startswith(b'\x7fELF'):
            continue
        a = elf_arch_string(body)
        m = re.search(r'xw\d+p\d+', a) if a else None
        seen.add(m.group(0) if m else '')
    seen.discard('')
    if not seen:
        return ''
    return sorted(seen)[0] if len(seen) == 1 else 'mixed:' + ','.join(sorted(seen))


def xwdiff(tmpdir):
    asm_set, legal = enumerate_xw_asm(tmpdir)
    groups = {}
    for scope, paths in collect_inputs().items():
        for rep, grp, _sha in dedup(paths):
            ver = archive_xw_version(rep) or '(undeclared)'
            g = groups.setdefault(ver, dict(archives=[], enc=Counter()))
            with open(rep, 'rb') as fh:
                data = fh.read()
            enc = Counter()
            for mname, body in ar_members(data):
                if not body.startswith(b'\x7fELF'):
                    continue
                for _sn, _ad, code in exec_sections(body):
                    for _c, _m, ln, raw, _o in scan(code):
                        if ln == 2 and in_xw_slot(raw):
                            enc[raw] += 1
            if enc:
                g['archives'].append((scope, os.path.relpath(rep, REPO), sum(enc.values())))
                g['enc'].update(enc)
    return asm_set, legal, groups


CONTROL_AR = os.path.join(EVT_ROOT, 'QingkeV4B_CH32V203_EVT', 'EXAM', 'ETH',
                          'NetLib', 'libwchnet.a')


def control():
    want = ['lui', 'lhu', 'andi', 'c.jr']
    with open(CONTROL_AR, 'rb') as fh:
        data = fh.read()
    for mname, body in ar_members(data):
        if not body.startswith(b'\x7fELF'):
            continue
        for sname, _addr, code in exec_sections(body):
            if sname != '.text.GetChipID':
                continue
            got = [(c, m) for c, m, _l, _r, _o in scan(code)]
            print('%s/%s: %s' % (mname, sname,
                                 ' '.join('%s(%s)' % (m, c) for c, m in got)))
            names = [m for _c, m in got]
            if names == want:
                print('control OK')
                return True
            print('control FAIL: expected %s' % want)
            return False
    print('control FAIL: .text.GetChipID not found')
    return False


# (path substring, expected XW instruction count) -- independently measured
# for this project; a mismatch means the slot table is wrong, not the corpus.
XW_CONTROLS = [
    ('libCH58xBLE.a', 5592),
    ('LIBMESHROM.a', 1750),
    ('CH32V317_EVT/EXAM/ETH/NetLib/libwchnet.a', 2274),
    ('CH32V317_EVT/EXAM/ETH/NetLib/libwchnet_float.a', 2274),
    ('LIBMESH.a', 0),
    ('libwchble.a', 0),
]


# --------------------------------------------------------------------------
# census
# --------------------------------------------------------------------------
def scan_archive(path):
    """Return (n_members, code_bytes, cat_mn Counter, unknown dict, archstrings)."""
    with open(path, 'rb') as fh:
        data = fh.read()
    counts = Counter()
    unknown = {}
    nmem = 0
    nbytes = 0
    arches = Counter()
    for mname, body in ar_members(data):
        if not body.startswith(b'\x7fELF'):
            continue
        nmem += 1
        arches[elf_arch_string(body) or '(none)'] += 1
        for sname, _addr, code in exec_sections(body):
            nbytes += len(code)
            for cat, mn, ln, raw, off in scan(code):
                counts[(cat, mn)] += 1
                if cat == 'unknown':
                    e = unknown.get(raw)
                    if e is None:
                        feats = feat16(raw) if ln == 2 else feat32(raw)
                        unknown[raw] = [mname, '%s+0x%x' % (sname, off), ln, feats, 1]
                    else:
                        e[4] += 1
    return nmem, nbytes, counts, unknown, arches


def census():
    inputs = collect_inputs()
    rows = []
    unk_rows = []
    summary = Counter()
    cover = []
    totals = dict(files=0, groups=0, members=0, bytes=0, insns=0)
    arch_all = Counter()
    per_archive = []

    for scope, paths in inputs.items():
        totals['files'] += len(paths)
        for rep, grp, sha in dedup(paths):
            totals['groups'] += 1
            nmem, nbytes, counts, unknown, arches = scan_archive(rep)
            totals['members'] += nmem
            totals['bytes'] += nbytes
            totals['insns'] += sum(counts.values())
            arch_all.update(arches)
            relrep = os.path.relpath(rep, REPO)
            sha16 = sha[:16]
            grel = [os.path.relpath(p, REPO) for p in grp]
            cover.append((scope, relrep, sha16, grel))
            per_archive.append((scope, relrep, nmem, counts, grel))
            for (cat, mn), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
                rows.append((scope, relrep, sha16, len(grp), nmem, cat, mn, n))
                summary[(cat, mn)] += n
            for raw, (mname, loc, ln, feats, n) in sorted(
                    unknown.items(), key=lambda kv: -kv[1][4]):
                unk_rows.append((scope, relrep, mname, loc, ln,
                                 '0x%0*x' % (ln * 2, raw), feats, n))

    prov = provenance()
    with open(os.path.join(RESULTS, 'isa-census.tsv'), 'w') as fh:
        fh.write('# RISC-V instruction census -- provenance\n')
        for k, v in prov.items():
            fh.write('# %-18s %s\n' % (k, v))
        fh.write('# rerun: python3 %s scan\n' % prov['script'])
        fh.write('# sha256 = SHA-256 of the whole .a file, first 16 hex digits;'
                 ' full value: shasum -a 256 <path>\n')
        fh.write('# content-group representative -> physical paths covered\n')
        for scope, rep, sha16, grp in cover:
            fh.write('# %s\t%s\t%s\t%d\t%s\n'
                     % (scope, rep, sha16, len(grp), ';'.join(grp)))
        fh.write('scope\trep_archive\tsha256_16\tn_paths\tn_members\tcategory\t'
                 'mnemonic_or_sig\tcount\n')
        for r in rows:
            fh.write('\t'.join(str(x) for x in r) + '\n')

    with open(os.path.join(RESULTS, 'isa-census-unknown.tsv'), 'w') as fh:
        fh.write('# RISC-V instruction census -- unidentified encodings\n')
        for k, v in prov.items():
            fh.write('# %-18s %s\n' % (k, v))
        fh.write('# join key to isa-census.tsv: (scope, rep_archive)\n')
        fh.write('scope\trep_archive\tmember\tsection+offset(first)\tlen\t'
                 'raw_hex\tfeatures\tcount\n')
        for r in unk_rows:
            fh.write('\t'.join(str(x) for x in r) + '\n')

    return totals, summary, unk_rows, per_archive, arch_all, cover


INSN_RE = re.compile(r'^\s*[0-9a-f]+:\t')


def xcheck(paths):
    """objdump cross-reference: total insn lines, undecoded, phantom fld/fsd."""
    out = []
    for p in paths:
        r = subprocess.run([OBJDUMP, '-d', p], capture_output=True, text=True)
        lines = [l for l in r.stdout.splitlines() if INSN_RE.match(l)]
        und = sum(1 for l in lines if '\t.2byte' in l or '\t.insn' in l)
        phantom = sum(1 for l in lines
                      if re.search(r'\t(c\.)?f(ld|sd)(sp)?\s', l))
        nmem, nbytes, counts, unknown, arches = scan_archive(p)
        mine = sum(counts.values())
        xw = sum(n for (c, _m), n in counts.items() if c == 'XW')
        # objdump collapses runs of zero bytes to a single "..." line, so it
        # under-reports by exactly the number of 0x0000 padding halfwords.
        zeros = counts.get(('unknown', 'q=0,f3=0,b65=0'), 0)
        out.append(dict(path=os.path.relpath(p, REPO), members=nmem,
                        mine=mine, objdump=len(lines), zeros=zeros,
                        delta=mine - len(lines) - zeros,
                        undecoded=und, phantom_fld_fsd=phantom, xw=xw,
                        xw_split_ok=(und + phantom == xw),
                        attrs=('none' if list(arches) == ['(none)'] else
                               ','.join(sorted(arches)))))
    return out


def main(argv):
    cmd = argv[1] if len(argv) > 1 else 'scan'
    if cmd == 'selftest':
        tmp = argv[2] if len(argv) > 2 else '.'
        raise SystemExit(0 if selftest(tmp) else 1)
    if cmd == 'control':
        raise SystemExit(0 if control() else 1)
    if cmd == 'xcheck':
        for d in xcheck(argv[2:]):
            print('\t'.join('%s=%s' % kv for kv in d.items()))
        return
    if cmd == 'inventory':
        for scope, paths in collect_inputs().items():
            print('%s: %d files, %d content groups'
                  % (scope, len(paths), len(dedup(paths))))
        return
    if cmd == 'provenance':
        for k, v in provenance().items():
            print('%-20s %s' % (k, v))
        return
    if cmd == 'xwdiff':
        tmp = argv[2] if len(argv) > 2 else '.'
        asm_set, legal, groups = xwdiff(tmp)
        print('XW 1.0 encodings the bundled GAS can emit: %d distinct '
              '(from %d accepted asm lines)'
              % (len(asm_set), sum(len(v) for v in asm_set.values())))
        for mn in XW_MNEMONICS:
            print('   %-9s legal operand forms: %d' % (mn, len(legal.get(mn, []))))
        # Test power: a slot already saturated by 1.0 cannot reveal a 2.2-only
        # encoding at all -- only a semantic redefinition, which bytes can't show.
        slots = [(0, 1), (0, 4), (0, 5), (2, 1), (2, 5)]
        per = 1 << 11    # 16 bits - 2 quadrant - 3 funct3
        print('\ndiscriminating power (each slot holds 2^11 = %d encodings):' % per)
        for q, f3 in slots:
            n = sum(1 for e in asm_set if (e & 3) == q and (e >> 13) & 7 == f3)
            print('   q=%d f3=%d  1.0 covers %5d (%5.1f%%)  detectable-as-2.2-only %5d'
                  % (q, f3, n, 100.0 * n / per, per - n))
        print('   total     1.0 covers %5d of %d (%.1f%%)'
              % (len(asm_set), len(slots) * per,
                 100.0 * len(asm_set) / (len(slots) * per)))
        for ver in sorted(groups):
            g = groups[ver]
            tot = sum(g['enc'].values())
            inside = {e: n for e, n in g['enc'].items() if e in asm_set}
            outside = {e: n for e, n in g['enc'].items() if e not in asm_set}
            print('\n=== declared version: %s === %d archives, %d slot insns, '
                  '%d distinct' % (ver, len(g['archives']), tot, len(g['enc'])))
            print('  in 1.0 set     : %6d distinct / %8d occurrences'
                  % (len(inside), sum(inside.values())))
            print('  NOT in 1.0 set : %6d distinct / %8d occurrences'
                  % (len(outside), sum(outside.values())))
            for q, f3 in slots:
                sub = {e: n for e, n in g['enc'].items()
                       if (e & 3) == q and (e >> 13) & 7 == f3}
                if not sub:
                    continue
                o = {e: n for e, n in sub.items() if e not in asm_set}
                print('    q=%d f3=%d  distinct=%-5d occ=%-7d outside1.0: %d/%d'
                      % (q, f3, len(sub), sum(sub.values()),
                         len(o), sum(o.values())))
            for e, n in sorted(outside.items(), key=lambda kv: -kv[1])[:30]:
                print('     0x%04x  x%-7d q=%d f3=%d b12=%d b[11:10]=%d '
                      'b[6:5]=%d b[9:7]=%d b[4:2]=%d'
                      % (e, n, e & 3, (e >> 13) & 7, (e >> 12) & 1,
                         (e >> 10) & 3, (e >> 5) & 3, (e >> 7) & 7, (e >> 2) & 7))
            for s, p, n in sorted(g['archives'], key=lambda x: -x[2]):
                print('     %-6s %6d  %s' % (s, n, p))
        return
    totals, summary, unk_rows, per_archive, arch_all, cover = census()
    print('files=%(files)d groups=%(groups)d members=%(members)d '
          'code_bytes=%(bytes)d insns=%(insns)d' % totals)
    bycat = Counter()
    for (cat, _mn), n in summary.items():
        bycat[cat] += n
    for cat, n in bycat.most_common():
        print('%-10s %10d  %5.2f%%  (%d distinct)'
              % (cat, n, 100.0 * n / totals['insns'],
                 sum(1 for c, _m in summary if c == cat)))
    print('unknown rows=%d distinct encodings=%d'
          % (len(unk_rows), len({r[5] for r in unk_rows})))
    # XW control numbers. Match on any physical path in the content group:
    # dedup can elect e.g. libMESH.a as representative of a group that also
    # holds LIBMESH.a, so keying on the representative's basename alone misses.
    bad = 0
    for want_sub, want_n in XW_CONTROLS:
        hit = False
        for _s, rep, _nm, counts, grel in per_archive:
            if not any(want_sub in g for g in grel):
                continue
            hit = True
            got = sum(n for (c, _m), n in counts.items() if c == 'XW')
            good = got == want_n
            bad += not good
            print('XWCHECK %-42s want=%-6d got=%-6d %s'
                  % (want_sub, want_n, got, 'OK' if good else '<-- MISMATCH'))
        if not hit:
            bad += 1
            print('XWCHECK %-42s NOT FOUND' % want_sub)
    print('XW controls: %s' % ('all OK' if not bad else '%d FAILED' % bad))


if __name__ == '__main__':
    main(sys.argv)
