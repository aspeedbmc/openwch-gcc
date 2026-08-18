void lto_xw_global(void);
void lto_xw_added(void);
void lto_xw_versioned(void);

void _start(void)
{
  lto_xw_global();
  lto_xw_added();
  lto_xw_versioned();
}
