"""Shared constants and helpers for the v2 and v4 builders; no device access."""
from pathlib import Path
import hashlib,struct,subprocess,json
P=Path(__file__).resolve().parent
ROOT=P.parent
FW=ROOT/'固件'
RECORDS=ROOT/'记录'
BACKUPS=ROOT/'备份'
ORIGINAL=FW/'YOGO75PRO-v1.26-original.bin'
EXPECTED='a20bc774d12f0a627a150d35d5efb0893ae95e20c6e16fcebe03111c031c5725'
BASE=0x02027000; TARGET=0x020343ec; OFFSET=TARGET-BASE+128
APPEND=0x02050f30

def crc16_modbus(data):
    crc=0xffff
    for byte in data:
        crc^=byte
        for _ in range(8):crc=(crc>>1)^ (0xa001 if crc&1 else 0)
    return crc

def verify_image(b):
    assert b[:8]==b'INGCHIPS'
    assert struct.unpack_from('<I',b,106)[0]==BASE
    assert struct.unpack_from('<I',b,110)[0]==len(b)-128
    block=struct.unpack_from('<H',b,66)[0]
    assert block==256
    assert struct.unpack_from('<I',b,68)[0]==(len(b)-128+block-1)//block
    assert struct.unpack_from('>H',b,62)[0]==crc16_modbus(b[128:]), 'payload CRC mismatch'
    assert struct.unpack_from('>H',b,126)[0]==crc16_modbus(b[:126]), 'header CRC mismatch'

def read_text_section(obj):
    b=obj.read_bytes()
    assert b[:6]==b'\x7fELF\x01\x01'
    assert struct.unpack_from('<H',b,18)[0]==40
    off=struct.unpack_from('<I',b,32)[0]
    entsize,count,names_idx=struct.unpack_from('<HHH',b,46)
    sections=[struct.unpack_from('<10I',b,off+i*entsize) for i in range(count)]
    ns=sections[names_idx];names=b[ns[4]:ns[4]+ns[5]]
    texts=[]
    for s in sections:
        name=names[s[0]:].split(b'\0',1)[0]
        if s[1] in (4,9) and s[5]:raise ValueError('unresolved relocations: '+str(name))
        if name==b'.text':texts.append(b[s[4]:s[4]+s[5]])
    assert len(texts)==1
    return texts[0]

def assemble(source,obj):
    subprocess.run(['xcrun','clang','-target','armv7em-none-eabi','-c',str(source),'-o',str(obj)],check=True)
    return read_text_section(obj)
