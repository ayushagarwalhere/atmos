import { spawn } from 'node:child_process';
import { pythonRuntime } from './python-runtime.mjs';
const root = process.cwd();
const python = pythonRuntime();
if (!python) { console.error('Create .venv-atmos and install requirements.txt first. See README.md.'); process.exit(1); }
const children=[];
function start(command,args) {
  const child=spawn(command,args,{cwd:root,stdio:'inherit',env:process.env});
  children.push(child);
  child.on('error',error=>{console.error(error.message);stop(1)});
  child.on('exit',code=>{if(code)stop(code)});
}
let stopping=false;
function stop(code=0) {if(stopping)return;stopping=true;children.forEach(child=>child.kill());process.exitCode=code;}
process.on('SIGINT',()=>stop());process.on('SIGTERM',()=>stop());process.on('exit',()=>children.forEach(child=>child.kill()));
if(process.argv[2]==='test')start(python,['-m','pytest','backend/tests','-q']);
else if(process.argv[2]==='demo')start(python,['-m','scripts.prepare_demo']);
else {
  start(python,['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8000']);
  if(process.argv[2]==='full')start(process.execPath,['node_modules/vite/bin/vite.js','--configLoader','native','--host','127.0.0.1']);
}
