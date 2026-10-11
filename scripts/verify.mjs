import { spawnSync } from 'node:child_process';
import { pythonRuntime } from './python-runtime.mjs';
const python=pythonRuntime();
if(!python){console.error('Create .venv-atmos and install requirements.txt first.');process.exit(1)}
for(const [command,args] of [[python,['-m','pytest','backend/tests','-q']],[process.execPath,['node_modules/vite/bin/vite.js','build','--configLoader','native']]]) {
  const result=spawnSync(command,args,{stdio:'inherit',env:process.env});
  if(result.error){console.error(result.error.message);process.exit(1)}
  if(result.status!==0)process.exit(result.status||1);
}
