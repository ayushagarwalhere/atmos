import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
// Resolve dependency imports in Node so esbuild does not enumerate restricted parent directories.
const workspaceResolver = {name:'workspace-resolver',setup(build){build.onResolve({filter:/.*/},args=>{try {if(args.path === '@react-three/fiber') return {path:path.resolve('node_modules/@react-three/fiber/dist/react-three-fiber.esm.js')}; if(args.path === 'fflate') return {path:path.resolve('node_modules/fflate/esm/browser.js')}; const require=createRequire(args.importer || path.join(process.cwd(),'package.json')); if(!args.path.startsWith('.') && !path.isAbsolute(args.path) && args.kind !== 'require-call'){const name=args.path.startsWith('@')?args.path.split('/').slice(0,2).join('/'):args.path.split('/')[0]; if(args.path===name){const dir=path.join(process.cwd(),'node_modules',name);const pkg=JSON.parse(fs.readFileSync(path.join(dir,'package.json'),'utf8'));if(pkg.module)return {path:path.join(dir,pkg.module)};}} if(!args.path.startsWith('.') && !path.isAbsolute(args.path) && args.kind !== 'require-call'){return {path:fileURLToPath(import.meta.resolve(args.path))};} return {path:require.resolve(args.path)};}catch{return undefined;}});}};
export default defineConfig({plugins:[react()],server:{proxy:{'/api':{target:process.env.ATMOS_API_PROXY_TARGET||'http://127.0.0.1:8000',changeOrigin:true}}},optimizeDeps:{esbuildOptions:{plugins:[workspaceResolver]}},build:{chunkSizeWarningLimit:1500}});
