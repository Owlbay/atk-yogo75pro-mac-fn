#!/usr/bin/python3
"""Device-scoped, non-capturing Fn map maintenance. Runs once and exits.
No HID reads, keyboard hooks, network, or firmware commands.
"""
import json,re,subprocess,sys
# USB identity and names from this keyboard's official firmware.
# Bluetooth identity was observed on ATK Yogo75 Pro-2 on 2026-09-23.
TARGETS=[('USB',{'VendorID':14139,'ProductID':4507,'Product':'ATK Yogo75 PRO','Transport':'USB'})]
TARGETS += [(f'Bluetooth slot {slot}',{'VendorID':14000,'ProductID':12292,'Product':f'ATK Yogo75 Pro-{slot}','Transport':'Bluetooth Low Energy'}) for slot in (1,2,3)]
SRC=0x700000073;DST=0xff00000003

def parse_services(text):
 matches=list(re.finditer(r'(?m)^([0-9a-fA-F]+)\s+UserKeyMapping\s+',text));services=[]
 for i,m in enumerate(matches):
  body=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
  pairs=[]
  for block in re.findall(r'\{([^{}]+)\}',body):
   a=re.search(r'HIDKeyboardModifierMappingSrc\s*=\s*(\d+)',block);b=re.search(r'HIDKeyboardModifierMappingDst\s*=\s*(\d+)',block)
   if not a or not b:raise ValueError('Unrecognized mapping syntax; refusing to replace')
   pairs.append((int(a.group(1)),int(b.group(1))))
  if not pairs and '(null)' not in body and not re.fullmatch(r'\s*\(\s*\)\s*',body):raise ValueError('Unrecognized empty property')
  services.append(tuple(sorted(set(pairs))))
 return services

def desired(services):
 if not services:return None
 others=[]
 for pairs in services:
  if any(a==SRC and b!=DST for a,b in pairs):raise ValueError('F24 has a different user mapping; preserving it')
  others.append(tuple((a,b) for a,b in pairs if a!=SRC))
 if len(set(others))!=1:raise ValueError('Different mappings on device interfaces; preserving them')
 goal=tuple(sorted(others[0]+((SRC,DST),)))
 return None if all(pairs==goal for pairs in services) else goal

def run(match,args):
 p=subprocess.run(['/usr/bin/hidutil','property','--matching',json.dumps(match,separators=(',',':'))]+args,text=True,capture_output=True,timeout=8)
 if p.returncode:raise RuntimeError(p.stderr.strip() or 'hidutil failed')
 return p.stdout

def ensure_target(label,match):
 goal=desired(parse_services(run(match,['--get','UserKeyMapping'])))
 if goal is None:return
 payload={'UserKeyMapping':[{'HIDKeyboardModifierMappingSrc':a,'HIDKeyboardModifierMappingDst':b} for a,b in goal]}
 run(match,['--set',json.dumps(payload)])
 services=parse_services(run(match,['--get','UserKeyMapping']))
 if not services or any(pairs!=goal for pairs in services):raise RuntimeError('Mapping readback mismatch')
 print(f'ATK Yogo75 PRO ({label}): device-only F24 -> Fn mapping applied')

def main():
 errors=[]
 for label,match in TARGETS:
  try:ensure_target(label,match)
  except Exception as e:errors.append(f'{label}: {e}')
 if errors:raise RuntimeError('; '.join(errors))
if __name__=='__main__':
 try:main()
 except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
