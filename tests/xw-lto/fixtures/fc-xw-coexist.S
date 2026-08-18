	.text
	.option rvc
	.globl fc_xw_coexist
	.type fc_xw_coexist, @function
fc_xw_coexist:
	c.flw fa0, 0(a1)
	c.lbu a0, 0(a1)
	ret
	.size fc_xw_coexist, .-fc_xw_coexist
