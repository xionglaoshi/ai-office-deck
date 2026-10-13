#!/usr/bin/env python3
"""Generate a private self-host config. Writes no secrets to stdout and never starts a server."""
import argparse,pathlib,json,secrets,hashlib,getpass,os
p=argparse.ArgumentParser();p.add_argument('--public-url',required=True);p.add_argument('--password-prompt',action='store_true');a=p.parse_args();root=pathlib.Path(__file__).resolve().parent
from urllib.parse import urlparse
u=urlparse(a.public_url)
if u.scheme not in ('http','https') or not u.netloc or u.path not in ('','/'):raise ValueError('Use a scheme and origin only')
if u.scheme=='http' and u.hostname not in ('localhost','127.0.0.1','::1'):raise ValueError('Remote access requires HTTPS')
output=root/'.dev.vars';handoff=root/'.selfhost-owner.json'
if output.exists() or handoff.exists():raise RuntimeError('Existing private config: preserve or rotate deliberately; never overwrite')
password=getpass.getpass('设置至少24字符的随机所有者密码: ') if a.password_prompt else secrets.token_urlsafe(32)
if len(password)<24:raise ValueError('Password too short')
service=secrets.token_urlsafe(48);session=secrets.token_urlsafe(48)
values=dict(SELF_HOSTED='1',OFFICE_PUBLIC_URL=a.public_url.rstrip('/'),OWNER_PASSWORD_HASH=hashlib.sha256(password.encode()).hexdigest(),OWNER_SESSION_KEY=session,OFFICE_SERVICE_TOKEN=service)
for path,text in [(output,'\n'.join(k+'='+json.dumps(v) for k,v in values.items())+'\n'),(handoff,json.dumps({'ownerPassword':password,'serviceToken':service},indent=2)+'\n')]:
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:f.write(text)
print(json.dumps({'configured':True,'secretsPrinted':False,'privateHandoff':str(handoff),'notStarted':True}))
