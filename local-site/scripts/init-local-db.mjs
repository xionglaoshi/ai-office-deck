import {spawnSync} from 'node:child_process';
// Use a recorded migration journal rather than replaying ALTER TABLE blindly.
const result=spawnSync(process.execPath,['--import','./scripts/sites-env.mjs','./node_modules/wrangler/bin/wrangler.js','d1','migrations','apply','DB','--local','--config','selfhost-db.json','--persist-to','.wrangler/state'],{stdio:'inherit',env:{...process.env,WRANGLER_SEND_METRICS:'false'}});
process.exit(result.status??1);
