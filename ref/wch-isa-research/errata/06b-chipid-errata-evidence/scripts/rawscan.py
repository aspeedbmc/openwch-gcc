#!/usr/bin/env python3
"""Independent raw-byte scanner: no objdump. Verifies CSR/address negatives."""
import sys, os, struct, glob, hashlib

def ar_members(data):
    """Yield (name, bytes) from a Unix ar archive."""
    if not data.startswith(b'!<arch>\n'):
        return
    off = 8
    longnames = b''
    while off + 60 <= len(data):
        hdr = data[off:off+60]
        if len(hdr) < 60:
            break
        name = hdr[0:16].decode('latin1').rstrip()
        try:
            size = int(hdr[48:58].decode('latin1').strip())
        except ValueError:
            break
        body = data[off+60:off+60+size]
        if name.startswith('//'):
            longnames = body
        elif name.startswith('/') and name[1:].isdigit():
            idx = int(name[1:])
            end = longnames.find(b'/\n', idx)
            if end < 0:
                end = longnames.find(b'\n', idx)
            nm = longnames[idx:end].decode('latin1').rstrip('/')
            yield nm, body
        elif not name.startswith('/'):
            yield name.rstrip('/'), body
        off += 60 + size + (size & 1)

def exec_sections(elf):
    """Yield (name, addr, bytes) for SHF_EXECINSTR sections of a 32-bit LE ELF."""
    if len(elf) < 52 or elf[:4] != b'\x7fELF' or elf[4] != 1 or elf[5] != 1:
        return
    e_shoff, = struct.unpack_from('<I', elf, 32)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('<HHH', elf, 46)
    if e_shoff == 0 or e_shnum == 0:
        return
    secs = []
    for i in range(e_shnum):
        o = e_shoff + i*e_shentsize
        if o+40 > len(elf):
            return
        nm, typ, flags, addr, off, size = struct.unpack_from('<IIIIII', elf, o)
        secs.append((nm, typ, flags, addr, off, size))
    if e_shstrndx >= len(secs):
        return
    stroff, strsize = secs[e_shstrndx][4], secs[e_shstrndx][5]
    strtab = elf[stroff:stroff+strsize]
    for nm, typ, flags, addr, off, size in secs:
        if (flags & 0x4) and typ == 1 and size:  # SHF_EXECINSTR, SHT_PROGBITS
            end = strtab.find(b'\0', nm)
            name = strtab[nm:end].decode('latin1')
            yield name, addr, elf[off:off+size]

CSR_NAMES = {0xF11:'mvendorid',0xF12:'marchid',0xF13:'mimpid',0xF14:'mhartid',
             0x301:'misa',0x341:'mepc',0x300:'mstatus',0x305:'mtvec',0x342:'mcause',
             0x343:'mtval',0x304:'mie',0x344:'mip',0x7C0:'?7C0',0x800:'gintenr',
             0x804:'intsyscr',0xBC0:'corecfgr',0xFC0:'?FC0'}

def scan(code, base):
    """Linear sweep honoring RVC length rule. Returns (csr_hits, addr_hits, xw_suspect, n_insn)."""
    csr_hits, addr_hits = [], []
    xw = 0; n = 0; i = 0
    L = len(code)
    while i + 1 < L:
        half = code[i] | (code[i+1] << 8)
        if (half & 3) != 3:
            # 16-bit compressed
            op = half & 3; f3 = (half >> 13) & 7
            # WCH XW slots (verified against GAS -march=rv32imac_xw):
            #   C0 f3=1/5  -> c.lbu / c.sb        (fld/fsd slots)
            #   C2 f3=1/5  -> c.lhu / c.sh        (fldsp/fsdsp slots)
            #   C0 f3=4    -> c.lbusp/c.lhusp/c.sbsp/c.shsp  (RVC reserved slot)
            # Omitting the f3=4 group undercounts XW and silently drops every
            # stack spill/reload path -- which is how an ID value propagates.
            if (op == 0 and f3 in (1, 4, 5)) or (op == 2 and f3 in (1, 5)):
                xw += 1
            i += 2; n += 1
            continue
        if i + 3 >= L:
            break
        w = struct.unpack_from('<I', code, i)[0]
        if (w & 0x1F) == 0x1F:   # >=48-bit encodings: bail conservatively
            i += 2; continue
        opc = w & 0x7F
        f3 = (w >> 12) & 7
        if opc == 0x73 and f3 in (1,2,3,5,6,7):
            csr = (w >> 20) & 0xFFF
            rd = (w >> 7) & 0x1F
            rs1 = (w >> 15) & 0x1F
            csr_hits.append((base+i, csr, CSR_NAMES.get(csr,'?'), f3, rd, rs1))
        elif opc in (0x37, 0x17):  # LUI / AUIPC
            imm = w & 0xFFFFF000
            if (0x1FFFF000 <= imm <= 0x1FFFFFFF or 0x40000000 <= imm <= 0x4002FFFF
                    or 0xE0000000 <= imm <= 0xE00FFFFF):
                addr_hits.append((base+i, 'lui' if opc==0x37 else 'auipc', imm, (w>>7)&0x1F))
        i += 4; n += 1
    return csr_hits, addr_hits, xw, n

def main(paths):
    print(f"{'archive':<40} {'members':>7} {'insn':>8} {'XW?':>7} {'CSR':>4} {'addr':>5}  detail")
    for p in sorted(paths):
        try:
            data = open(p,'rb').read()
        except OSError as e:
            # Fail loudly: an audit scanner must never silently skip an input.
            # (Paths with spaces truncated by awk/cut land here.)
            print(f"ERROR unreadable: {p}: {e}", file=sys.stderr)
            print(f"{os.path.basename(p):<40} {'ERR':>7} {'-':>8} {'-':>7} {'-':>4} {'-':>5}  UNREADABLE")
            continue
        tot_csr, tot_addr, tot_xw, tot_n, nm = [], [], 0, 0, 0
        for mname, body in ar_members(data):
            if not body.startswith(b'\x7fELF'):
                continue
            nm += 1
            for sname, addr, code in exec_sections(body):
                c,a,x,n = scan(code, 0)
                tot_csr += [(mname,sname)+h for h in c]
                tot_addr += [(mname,sname)+h for h in a]
                tot_xw += x; tot_n += n
        det = ''
        if tot_csr:
            det = ' CSR:' + ','.join(sorted({f"{h[3]:#x}({h[4]})" for h in tot_csr}))
        if tot_addr:
            det += ' ADDR:' + ','.join(sorted({f"{h[4]:#x}" for h in tot_addr}))
        print(f"{os.path.basename(p):<40} {nm:>7} {tot_n:>8} {tot_xw:>7} {len(tot_csr):>4} {len(tot_addr):>5} {det}")
        for h in tot_csr:
            print(f"    CSR @{h[0]}/{h[1]}+{h[2]:#x}: csr={h[3]:#x} {h[4]} f3={h[5]} rd={h[6]} rs1={h[7]}")

if __name__ == '__main__':
    main(sys.argv[1:])
