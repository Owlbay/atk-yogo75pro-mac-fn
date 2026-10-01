.syntax unified
.thumb
.cpu cortex-m4
.section .text
/* Origin 0x02050f30. F24 is transported in the keyboard report independently
   of Consumer media reports. macOS maps this device's F24 to native Fn. */
patch_start:
 cmp r0, #2
 bne original
 ldr r3, state_ptr
 ldrb r1, [r3, #7]
 cbnz r1, original
 ldrb.w r1, [r3, #0x8c]
 cbnz r1, f24
 ldr r1, mode_ptr
 ldrb r1, [r1]
 cmp r1, #1
 bne original
f24:
 strb.w r2, [r3, #0x8c]
 movs r0, #0
 movs r1, #0x73
 b.w patch_start + (0x020422e0 - 0x02050f30)
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
