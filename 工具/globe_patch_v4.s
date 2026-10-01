.syntax unified
.thumb
.cpu cortex-m4
.section .text
/* Origin 0x02050f30. Revision v4: Mac Fn is sent as Consumer 0x029D (Globe)
   through the original media report; no host mapping required. Layout up to
   win_return is identical to v2 so the v2 trampolines keep their addresses. */
patch_start:
 cmp r0, #2
 bne original
 ldr r3, state_ptr
 ldrb r1, [r3, #7]
 cbnz r1, original
 ldrb.w r1, [r3, #0x8c]
 cbnz r1, fn_mac
 ldr r1, mode_ptr
 ldrb r1, [r1]
 cmp r1, #1
 bne original
fn_mac:
 strb.w r2, [r3, #0x8c]
 b.w globe
 nop
 nop
original:
 push {r7, lr}
 sub sp, #0xa0
 b.w patch_start + (0x020343f0 - 0x02050f30)
/* At physical key-down, cache media-vs-standard with the original per-key
   layer in bit 7. This retains the selected behavior until key release. */
.balign 4
setter:
 ldrb r1, [r0, #4]
 ldrb r2, [r0]
 cmp r2, #1
 blo store_layer
 cmp r2, #12
 bhi store_layer
 ldr r3, mode_ptr
 ldrb r3, [r3]
 cmp r3, #1
 bne store_layer
 ldrb.w r3, [r0, #0x8c]
 cbz r3, store_layer
 orr r1, r1, #0x80
store_layer:
 add r2, r0
 strb r1, [r2, #0xb]
 ldrb.w r1, [sp, #0x57]
 ldr.w pc, setter_return
.balign 4
getter:
 ldrb r1, [r1, #0xb]
 strb r1, [r0, #0xa]
 movs r1, #0
 str r1, [sp, #0x50]
 ldrb r0, [r0, #0xa]
 and r0, r0, #3
 mov r1, r0
 ldr.w pc, getter_return
.balign 4
row_gate:
 ldrb.w r0, [r0, #0x27]
 cmp r0, #1
 bne win_path
 ldr r3, state_ptr
 ldrb r1, [r3]
 cmp r1, #1
 blo mac_path
 cmp r1, #12
 bhi mac_path
 ldrb r1, [r3, #0xa]
 tst r1, #0x80
 beq win_path
mac_path:
 ldr.w pc, mac_return
win_path:
 ldr.w pc, win_return
.balign 4
state_ptr: .word 0x200095a4
mode_ptr: .word 0x200077a1
setter_return: .word 0x200044ff
getter_return: .word 0x20004555
mac_return: .word 0x200045db
win_return: .word 0x20004c5d
/* Globe press: Consumer 0x029D. On release (r2 is already 0) clear the media
   slot only if it still holds Globe, so a held Fn+F-row media key is not cut
   off. None of the F-row media usages has low byte 0x9D. */
globe:
 cbz r2, globe_up
 movs r0, #0x9d
 movs r1, #0x02
 b.w patch_start + (0x02033ea4 - 0x02050f30)
globe_up:
 ldr r0, report_ptr
 ldrb r1, [r0, #0x2b]
 cmp r1, #0x9d
 bne globe_done
 b.w patch_start + (0x02033ea4 - 0x02050f30)
globe_done:
 bx lr
.balign 4
report_ptr: .word 0x20008508
