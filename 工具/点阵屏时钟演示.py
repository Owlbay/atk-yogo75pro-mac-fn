"""Wired-only demo: scrolling clock on the YOGO 75 PRO 6x6 dot screen.
Uses only the realtime frame command (0x3C); nothing is written to flash.
The keyboard reverts to its own effect ~0.5 s after the last frame.
Usage: 点阵屏时钟演示.py [--seconds N] [--no-pattern]
"""
import argparse,time,struct
from probe_device import connect,request

W=H=6
FONT={  # 3x5 digits, rows top->bottom, bit2=left
 '0':[7,5,5,5,7],'1':[2,6,2,2,7],'2':[7,1,7,4,7],'3':[7,1,7,1,7],'4':[5,5,7,1,1],
 '5':[7,4,7,1,7],'6':[7,4,7,5,7],'7':[7,1,1,1,1],'8':[7,5,7,5,7],'9':[7,5,7,1,7]}

def rgb565(r,g,b):return (r>>3)<<11|(g>>2)<<5|(b>>3)

def send(h,cmd,offset=0,data=b''):
 p=bytearray(64);p[0]=0xaa;p[1]=cmd;struct.pack_into('<H',p,2,offset);p[4]=len(data);p[8:8+len(data)]=data
 h.write(b'\0'+bytes(p))
 h.read(65,5)  # drain an ACK if the firmware sends one

def push(h,pixels):
 """pixels: 36 (r,g,b) tuples, row-major from top-left."""
 data=b''.join(struct.pack('<H',rgb565(*c)) for c in pixels)
 send(h,0x3c,0,data[:56]);send(h,0x3c,56,data[56:72])

def columns(text,color,colon_on):
 cols=[]
 for ch in text:
  if ch==':':cols.append([(c if colon_on and r in(1,3) else None) for r,c in enumerate([color]*5)]);cols.append([None]*5);continue
  g=FONT[ch]
  for x in range(3):cols.append([color if g[r]>>(2-x)&1 else None for r in range(5)])
  cols.append([None]*5)
 return cols

def clock_frame(t,scroll):
 lt=time.localtime(t);text=time.strftime('%H:%M',lt)
 cols=[[None]*5]*W+columns(text,(255,170,40),int(t*2)%2==0)
 start=scroll%len(cols)
 px=[]
 for r in range(H):
  for x in range(W):
   if r<5:
    c=cols[(start+x)%len(cols)][r];px.append(c or (0,0,0))
   else:  # bottom row: seconds progress, one dot per 10 s
    px.append((40,120,255) if x<lt.tm_sec//10+1 else (4,8,20))
 return px

def main():
 a=argparse.ArgumentParser();a.add_argument('--seconds',type=float,default=60);a.add_argument('--no-pattern',action='store_true');args=a.parse_args()
 h=connect();last_session=0
 try:
  request(h,0x10);last_session=time.monotonic()
  if not args.no_pattern:
   corner=[(0,0,0)]*36
   corner[0]=(255,0,0);corner[5]=(0,255,0);corner[30]=(0,0,255);corner[35]=(255,255,255)
   end=time.monotonic()+5
   while time.monotonic()<end:push(h,corner);time.sleep(0.1)
  end=time.monotonic()+args.seconds;scroll=0;tick=time.monotonic()
  while time.monotonic()<end:
   if time.monotonic()-last_session>2:request(h,0x10);last_session=time.monotonic()
   push(h,clock_frame(time.time(),scroll))
   if time.monotonic()-tick>=0.18:scroll+=1;tick=time.monotonic()
   time.sleep(0.05)
 finally:
  try:send(h,0x3d);request(h,0x11)
  finally:h.close()

if __name__=='__main__':main()
