import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
export function pythonRuntime(){
  const suffix=process.platform==='win32'?'Scripts/python.exe':'bin/python';
  const candidates=process.env.ATMOS_PYTHON
    ? [process.env.ATMOS_PYTHON]
    : ['.venv-atmos','.venv','.venv311'].map(directory=>path.resolve(directory,suffix)).filter(candidate=>existsSync(candidate));
  for(const candidate of candidates){
    // Recreating a venv with another Python version can leave incompatible native wheels.
    const result=spawnSync(candidate,['-c','import fastapi, pydantic_core, uvicorn'],{encoding:'utf8',timeout:30000,windowsHide:true});
    if(result.status===0)return candidate;
    const reason=result.error?.message || result.stderr?.trim().split(/\r?\n/).at(-1) || 'Dependency check failed';
    console.warn(`Skipping unusable Python environment ${candidate}: ${reason}`);
  }
}
