import assert from 'node:assert/strict';
import {dispatch} from './dispatch.mjs';
const request={thread_id:'test',client_id:'message1',message:'test'};
let disk={},adds=0,starts=0,entries=[],loseAdd=false,loseStart=false;
const persist=j=>{disk=structuredClone(j)};
async function rpc(method,p) {
 if(method==='thread/queue/list') return {data:entries};
 if(method==='thread/queue/add') {
  adds++;entries=[{id:'submission'+adds,clientUserMessageId:p.clientUserMessageId}];
  if(loseAdd) {entries=[];throw Error('accepted and consumed but response lost');}
  return {queuedSubmission:entries[0]};
 }
 if(method==='thread/queue/start') {starts++;entries=[];if(loseStart)throw Error('response lost');}
 return {};
}
loseAdd=true;
await assert.rejects(dispatch(request,{},persist,rpc));
assert.equal((await dispatch(request,structuredClone(disk),persist,rpc)).state,'delivery_uncertain');
assert.equal(adds,1); // restart cannot re-add an ambiguous submission
disk={};loseAdd=false;loseStart=true;
await dispatch(request,{},persist,rpc);
assert.equal((await dispatch(request,structuredClone(disk),persist,rpc)).state,'consumed_pending_ack');
assert.equal(adds,2);assert.equal(starts,1);
// A lost add response with entry still queued is recovered by client ID.
entries=[{id:'existing',clientUserMessageId:'message1'}];disk={add_attempted:true};loseStart=false;
assert.equal((await dispatch(request,disk,persist,rpc)).state,'started');assert.equal(adds,2);
// New message has its own journal and is submitted normally.
assert.equal((await dispatch({...request,client_id:'message2'},{},persist,rpc)).state,'started');
assert.equal(adds,3);
console.log('PASS: ambiguous add, lost start, restart, queue reconciliation, new message');
