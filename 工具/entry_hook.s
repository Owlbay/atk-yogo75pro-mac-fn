.syntax unified
.thumb
.cpu cortex-m4
.section .text
patch_start:
 b.w patch_start + (0x02050f30 - 0x020343ec)
