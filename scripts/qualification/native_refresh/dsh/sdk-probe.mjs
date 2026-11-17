/** Credential-free native DSH skill and configuration reload qualification. */
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync, readFileSync, rmSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
if (!process.argv[2]) throw new Error('An explicit runtime node_modules path is required');
const modules = join(resolve(process.argv[2]), '@deepseek-ai');
const load = name => import(pathToFileURL(join(modules, name, 'lib/index.js')).href);
const { Context } = await load('cordis');
const { default: SkillRegistry } = await load('dsh-skill');
const SkillFilesystem = await load('dsh-skill-filesystem');
const { default: Hmr } = await load('dsh-hmr');
const { default: Timer } = await load('cordis-plugin-timer');
const { boot, initProfile, readProfilePatches, recomposeProfile } = await load('dsh-app-boot');
const home = mkdtempSync(join(tmpdir(), 'houmao-dsh-refresh-probe-'));
const results = {pid: process.pid, version: JSON.parse(readFileSync(join(modules,'dsh/package.json'),'utf8')).version};
const contexts = [];
function skill(root, name, desc, body) {const dir=join(root,name);mkdirSync(dir,{recursive:true});writeFileSync(join(dir,'SKILL.md'),`---\nname: ${name}\ndescription: ${desc}\n---\n\n${body}\n`);}
async function skills(watch) {
 const root=join(home,'skills-'+watch);mkdirSync(root);skill(root,'alpha','initial','body-v1');
 const ctx=new Context(); contexts.push(ctx);ctx.baseUrl=pathToFileURL(home+'/').href;
 await ctx.plugin(SkillRegistry);await ctx.plugin(SkillFilesystem,{includeDefaultRoots:false,customSkillDirs:[root],watch,watchStabilityThresholdMs:10,watchPollIntervalMs:10});
 const initial=await ctx.skills.list({cwd:home});assert.equal(initial.length,1);
 skill(root,'alpha','updated','body-v2');skill(root,'beta','new','body-beta');
 const body=await ctx.skills.get('alpha',{cwd:home});assert.equal(body.content.trim(),'body-v2');
 await delay(500);
 const updated=await ctx.skills.list({cwd:home});
 rmSync(join(root,'alpha'),{recursive:true}); await delay(500);
 const removed=await ctx.skills.list({cwd:home});
 return {initial:initial.map(s=>s.name+':'+s.description),updated:updated.map(s=>s.name+':'+s.description),removed:removed.map(s=>s.name),body:body.content.trim()};
}
async function profile(mode) {
 const dir=join(home,mode,'profiles','probe');mkdirSync(dir,{recursive:true});initProfile(dir,[]);writeFileSync(join(dir,'cordis.yml'),'[]\n');
 const p={name:'probe',dir,patchPath:join(dir,'cordis.patch.yml'),home:join(home,mode),cwd:home,installAnchor:join(home,mode,'package.json'),startedBundles:[],overlays:[],telemetryDisabledEnv:undefined};
 const rows=()=>[{insert:[{id:'timer',name:'cordis:timer'},...(mode==='watched'?[{id:'hmr',name:'cordis:hmr',config:{root:[]}}]:[]),{id:'probe',name:'cordis:probe',config:{value:'initial'}}]}];
 writeFileSync(p.patchPath,JSON.stringify(rows()));
 let ready;
 const ctx=await boot('probe',join(dir,'cordis.yml'),readProfilePatches('probe',p),host=>{
   host.provide('profileContext',p);host.provide('appReady',{onReady(listener){ready=listener;return()=>{}}});
   host.loader.builtins.timer=Timer;host.loader.builtins.hmr=Hmr;
   host.loader.builtins.probe={apply(ctx,cfg){ctx.provide('refreshProbe',cfg.value)}};
 });contexts.push(ctx);ready?.();
 assert.equal(ctx.get('refreshProbe'),'initial');
 writeFileSync(p.patchPath,JSON.stringify(rows()).replace('initial','changed'));
 await delay(2900);
 const before=ctx.get('refreshProbe');
 let outcome;
 if(mode==='watched') outcome=await ctx.hmr.runExclusive(()=>ctx.hmr.reconcileProfile());
 else outcome=await recomposeProfile(ctx,readProfilePatches('probe',p),'probe');
 const after=ctx.get('refreshProbe');assert.equal(after,'changed');
 return {beforeExplicit:before,afterExplicit:after,outcome,pid:process.pid};
}
try {
 results.noWatch=await skills(false);assert.deepEqual(results.noWatch.updated,['alpha:initial']);assert.deepEqual(results.noWatch.removed,['alpha']);
 results.watch=await skills(true);assert.deepEqual(results.watch.updated,['alpha:updated','beta:new']);assert.deepEqual(results.watch.removed,['beta']);
 results.hmr=await profile('watched');assert.equal(results.hmr.beforeExplicit,'changed');
 results.explicitAppBoot=await profile('manual');assert.equal(results.explicitAppBoot.beforeExplicit,'initial');
 console.log(JSON.stringify(results,null,2));
} finally {for(const ctx of contexts.reverse())await ctx.fiber.dispose();rmSync(home,{recursive:true,force:true});}
