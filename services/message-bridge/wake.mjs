import fs from 'node:fs';
import {dispatch} from './dispatch.mjs';
const file=process.argv[2];
const request=JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
const receipt=file+'.delivery.json';
const journal=fs.existsSync(receipt)?JSON.parse(fs.readFileSync(receipt,'utf8')):{};
function persist(value) {
  const tmp=receipt+'.tmp';
  const fd=fs.openSync(tmp,'w');
  try {fs.writeFileSync(fd,JSON.stringify(value));fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
  fs.renameSync(tmp,receipt);
}
const ws=new WebSocket(request.endpoint || 'ws://127.0.0.1:18773');let seq=0;const pending=new Map();
const timer=setTimeout(()=>{console.log(JSON.stringify({state:'unavailable',error:'timeout'}));process.exit(2)},25000);
function rpc(method,params){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});}
ws.onmessage=e=>{const m=JSON.parse(e.data),p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result)}};
let result={state:'unavailable'};
try {
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=()=>reject(new Error('bridge connection unavailable'))});
 await rpc('initialize',{clientInfo:{name:'orbit-message-bridge',version:'2.0'},capabilities:{experimentalApi:true}});
 ws.send(JSON.stringify({method:'initialized'}));
 result=await dispatch(request,journal,persist,rpc);
} catch(e){result.error=e.message;}
finally{clearTimeout(timer);ws.close();console.log(JSON.stringify(result));}
