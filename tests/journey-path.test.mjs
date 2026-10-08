import assert from 'node:assert/strict';
import test from 'node:test';
import { sampleJourney } from '../src/components/journeyPath.js';
test('the camera passes through an open window before the pod appears',()=>{
 const approach=sampleJourney(.6),exit=sampleJourney(.67),reveal=sampleJourney(.9);
 assert.ok(approach.y>-25);assert.ok(exit.y<-25);assert.equal(approach.pitch,-Math.PI/2);
 assert.ok(Math.abs(approach.z-5)<.001);assert.ok(approach.sash>Math.PI/2-.001);
 assert.equal(approach.podVisible,false);assert.equal(exit.podVisible,false);assert.equal(reveal.podVisible,true);
 assert.ok(Math.abs(reveal.pitch)<.00001);assert.ok(reveal.z>approach.z);
});
test('camera positions remain continuous while emerging and reversing',()=>{
 for(const boundary of [.3,.68,.79,.85]){const a=sampleJourney(boundary-.00001),b=sampleJourney(boundary+.00001);assert.ok(Math.abs(a.y-b.y)<.01);assert.ok(Math.abs(a.z-b.z)<.01);assert.ok(Math.abs(a.pitch-b.pitch)<.01);}
 assert.deepEqual(sampleJourney(-1),sampleJourney(0));assert.deepEqual(sampleJourney(2),sampleJourney(1));
});
