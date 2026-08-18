__attribute__((noinline, noclone, used))
void lto_xw_global(void)
{
  __asm__ volatile ("c.lbu a0, 0(a1)" ::: "a0", "a1", "memory");
}

__attribute__((target("arch=+xw"), noinline, noclone, used))
void lto_xw_added(void)
{
  __asm__ volatile (
    "c.lbu a0, 0(a1)\n\t"
    "c.lhu a0, 2(a1)\n\t"
    "c.sb a0, 3(a1)\n\t"
    "c.sh a0, 4(a1)\n\t"
    "c.lbusp a0, 5(sp)\n\t"
    "c.lhusp a0, 6(sp)\n\t"
    "c.sbsp a0, 7(sp)\n\t"
    "c.shsp a0, 8(sp)\n\t"
    ::: "a0", "a1", "memory");
}

__attribute__((target("arch=rv32imac_xw9p9"), noinline, noclone, used))
void lto_xw_versioned(void)
{
  __asm__ volatile ("c.lbu a0, 0(a1)" ::: "a0", "a1", "memory");
}
