#!/usr/bin/env python3
"""Read/write owner-private Site data using Keychain; never print credentials."""
import argparse,json,pathlib,subprocess,urllib.request,sys
CONFIG=pathlib.Path(__file__).resolve().parent.parent/'config.json'
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['read','curate']);p.add_argument('--file');p.add_argument('--dry-run',action='store_true');a=p.parse_args();config=json.loads(CONFIG.read_text())
 if a.dry_run:
  if a.action=='curate':
   if not a.file:raise ValueError('--file required')
   json.loads(pathlib.Path(a.file).read_bytes())
  print(json.dumps({'dry_run':True,'action':a.action,'target':config['site_url']+('/api/sync' if a.action=='read' else '/api/curate'),'input':a.file},ensure_ascii=False));return
 token=json.loads(pathlib.Path(config['local_service_file']).read_text())['serviceToken']
 headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json'}
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':config['proxy'],'https':config['proxy']}))
 route='/api/sync' if a.action=='read' else '/api/curate';body=None
 if a.action=='curate':
  if not a.file:raise ValueError('--file required')
  body=pathlib.Path(a.file).read_bytes();json.loads(body)
 with opener.open(urllib.request.Request(config['site_url']+route,data=body,headers=headers),timeout=45) as r:data=json.load(r)
 if a.action=='curate':
  if not data.get('success'):raise RuntimeError('Curation not confirmed')
  with opener.open(urllib.request.Request(config['site_url']+'/api/sync',headers=headers),timeout=45) as r:result=json.load(r)
  if result.get('curated',{}).get('updated')!=data['updated']:raise RuntimeError('Curation readback failed')
  data['readbackVerified']=True
 print(json.dumps(data,ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'errorType':type(e).__name__}));sys.exit(1)
