	.text
	.option rvc
	.globl dc_xw_cfld
	.type dc_xw_cfld, @function
dc_xw_cfld:
	c.fld fa0, 0(a1)
	ret
	.size dc_xw_cfld, .-dc_xw_cfld
