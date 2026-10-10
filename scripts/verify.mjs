import { spawnSync } from 'node:child_process';
import path from 'node:path';
const python=path.resolve('.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
for(const [command,args] of [[python,['-m','pytest','backend/tests','-q']],[process.execPath,['node_modules/vite/bin/vite.js','build','--configLoader','native']]]) {
  const result=spawnSync(command,args,{stdio:'inherit',env:process.env});
  if(result.error){console.error(result.error.message);process.exit(1)}
  if(result.status!==0)process.exit(result.status||1);
}
