/** Native HMR pending/partial-effects probe, no credentials or model requests. */
import {value} from './node_modules/host-package/index.mjs';
import assert from 'node:assert/strict';
import {writeFileSync,readFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
if (!process.argv[2]) throw new Error('An explicit runtime node_modules path is required');
const base=join(resolve(process.argv[2]), '@deepseek-ai');
const load=n=>import(pathToFileURL(join(base,n,'lib/index.js')).href);
const {boot,initProfile,readProfilePatches}=await load('dsh-app-boot');
const {default:Hmr}=await load('dsh-hmr');
const {default:Timer}=await load('cordis-plugin-timer');
const dir=fileURLToPath(new URL('.',import.meta.url));
initProfile(dir,[]);writeFileSync(join(dir,'cordis.yml'),'[]\n');
const profile={name:'probe',dir,patchPath:join(dir,'cordis.patch.yml'),home:join(dir,'home'),cwd:dir,installAnchor:join(dir,'package.json'),startedBundles:[],overlays:[],telemetryDisabledEnv:undefined};
const rows=[{insert:[{id:'timer',name:'cordis:timer'},{id:'hmr',name:'cordis:hmr',config:{root:[]}},{id:'probe',name:'./probe.mjs',config:{value:'original'}}]}];
writeFileSync(join(dir,'probe.mjs'),'export const name="probe"; export function apply(ctx,cfg){ctx.get("trace").push("start:"+cfg.value);ctx.provide("probeValue",cfg.value);ctx.effect(()=>()=>ctx.get("trace").push("stop:"+cfg.value))}\n');
writeFileSync(profile.patchPath,JSON.stringify(rows));
const trace=[];let ready;
const ctx=await boot('probe',join(dir,'cordis.yml'),readProfilePatches('probe',profile),host=>{host.provide('profileContext',profile);host.provide('trace',trace);host.provide('appReady',{onReady(fn){ready=fn;return()=>{}}});host.loader.builtins.timer=Timer;host.loader.builtins.hmr=Hmr;});
try{
 ready?.();assert.equal(value,1);assert.equal(ctx.get('probeValue'),'original');trace.length=0;
 writeFileSync(join(dir,'node_modules/host-package/index.mjs'),'export const value=2;\n');
 rows[0].insert[2].config.value='partial-config';writeFileSync(profile.patchPath,JSON.stringify(rows));
 const pending=await ctx.hmr.runExclusive(()=>ctx.hmr.reconcileProfile());
 assert.ok(pending.pending.some(p=>p.reason==='host-module'));assert.equal(ctx.get('probeValue'),'partial-config');
 const restartWithPartial={pending,trace:[...trace],probeValue:ctx.get('probeValue'),hostValue:value,pid:process.pid};
 trace.length=0;
 writeFileSync(join(dir,'probe.mjs'),'export const name="probe"; export function apply(){throw new Error("controlled-bad-plugin")}\n');
 let failure;
 try{await ctx.hmr.runExclusive(()=>ctx.hmr.reconcileProfile());}catch(e){failure=e.message;}
 assert.ok(failure.includes('controlled-bad-plugin'));assert.ok(trace.includes('stop:partial-config'));assert.equal(ctx.get('probeValue'),undefined);
 console.log(JSON.stringify({restartWithPartial,replacementFailure:{failure,trace,probeValue:ctx.get('probeValue')??null,pid:process.pid}},null,2));
}finally{await ctx.fiber.dispose();}
