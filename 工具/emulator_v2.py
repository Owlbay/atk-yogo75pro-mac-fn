"""Execute original and patched ARM Thumb routines in Unicorn. NO DEVICE ACCESS."""
from pathlib import Path
import struct,json,random,hashlib
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import *
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB as CT,CS_MODE_MCLASS as CM
from build_patch_v2 import ORIGINAL,OUTPUT,BASE,P,verify_image,EXPECTED
RAM=0x20000000;RAMSIZE=0x20000;SP=RAM+0x1f000;STOP=0x020ff000
FN=0x020343ec;DISPATCH=0x02041ea4;MEDIA=0x02033ea4
CFG=0x200077a1;STATE=0x200095a4;REPORT=0x20008508
original=ORIGINAL.read_bytes();patched=OUTPUT.read_bytes()

class Emulator:
 def __init__(self,b):
  self.uc=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
  self.uc.mem_map(0x02000000,0x100000);self.uc.mem_write(BASE,b[128:])
  self.uc.mem_map(RAM,RAMSIZE)
  self.uc.mem_write(0x200043b8,b[0x0204da90-BASE+128:0x0204da90-BASE+128+0x33b0])
  self.calls=[];self.stop_on_original=False;self.stopped_original=False
  self.uc.hook_add(UC_HOOK_CODE,self.hook)
 def hook(self,uc,a,size,data):
  if a==STOP:uc.emu_stop()
  if a in (0x20007554,0x2000755e,0x200075b8):
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  if self.stop_on_original and a==FN+4:self.stopped_original=True;uc.emu_stop()
 def write(self,a,b):self.uc.mem_write(a,bytes(b))
 def read(self,a,n):return bytes(self.uc.mem_read(a,n))
 def set_byte(self,a,n):self.write(a,[n&255])
 def byte(self,a):return self.read(a,1)[0]
 def invoke(self,addr,*args):
  self.uc.reg_write(UC_ARM_REG_SP,SP);self.uc.reg_write(UC_ARM_REG_LR,STOP|1)
  regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
  for reg in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]:self.uc.reg_write(reg,0xabcdef00+reg)
  for reg,val in zip(regs,args):self.uc.reg_write(reg,val)
  self.uc.emu_start(addr|1,STOP,count=20000)
  if not self.stopped_original:
   assert self.uc.reg_read(UC_ARM_REG_PC)==STOP,hex(self.uc.reg_read(UC_ARM_REG_PC))
   assert self.uc.reg_read(UC_ARM_REG_SP)==SP,'stack imbalance'
   for reg in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]:assert self.uc.reg_read(reg)==0xabcdef00+reg,'callee-save corruption'
 def install_keymaps(self):
  for a,pos in [(0x20007f06,0x238b6),(0x20008086,0x23a36),(0x20008206,0x23bb6),(0x20008386,0x23d36)]:self.write(a,original[pos:pos+384])

