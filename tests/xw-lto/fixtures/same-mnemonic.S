	.text
	.option rvc
	.globl same_mnemonic
	.type same_mnemonic, @function
same_mnemonic:
	c.lbu a0, 0(a1)
	ret
	.size same_mnemonic, .-same_mnemonic
