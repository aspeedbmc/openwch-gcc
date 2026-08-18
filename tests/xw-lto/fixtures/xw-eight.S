	.text
	.option rvc
	.globl xw_eight
	.type xw_eight, @function
xw_eight:
	c.lbu a0, 0(a1)
	c.lhu a0, 2(a1)
	c.sb a0, 3(a1)
	c.sh a0, 4(a1)
	c.lbusp a0, 5(sp)
	c.lhusp a0, 6(sp)
	c.sbsp a0, 7(sp)
	c.shsp a0, 8(sp)
	ret
	.size xw_eight, .-xw_eight
