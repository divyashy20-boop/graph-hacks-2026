// Run with: node --test tests/test_force_graph.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const app = fs.readFileSync('ugi/assets/app.js', 'utf8');
const context = vm.createContext({});
vm.runInContext(app.slice(app.indexOf('function forceGraphData('), app.indexOf('function createOrbitRenderer(')), context);

test('event participants remain role-labelled event links; simulation cannot mutate source endpoints', () => {
  const data = {
    entities: ['a', 'b', 'c'].map(id => ({id, kind: 'Entity'})),
    claims: [{id: 'claim', subject_id: 'a', object_id: 'b', polarity: 'negative', modality: 'possible'}],
    events: [{id: 'event', kind: 'RelationEvent', participants: [
      {entity_id: 'a', role: 'provider'}, {entity_id: 'b', role: 'item'}, {entity_id: 'c', role: 'recipient'},
    ]}],
  };
  const before = JSON.stringify(data);
  const display = context.forceGraphData(data);
  assert.equal(display.nodes.length, 4);
  assert.equal(display.links.length, 4);
  assert.deepEqual(Array.from(display.links.filter(l => l.event), l => [l.source, l.target, l.role]), [
    ['event', 'a', 'provider'], ['event', 'b', 'item'], ['event', 'c', 'recipient'],
  ]);
  assert.equal(display.links[0].record, data.claims[0]);
  display.nodes[0].x = 50;
  display.links[0].source = display.nodes[0];
  assert.equal(JSON.stringify(data), before);
});

test('display limits exclude dangling links and partially visible events', () => {
  const data = {entities: Array.from({length: 61}, (_, i) => ({id: String(i)})),
    claims: [{subject_id: '0', object_id: '60'}],
    events: [{id: 'e', participants: [{entity_id: '0', role: 'a'}, {entity_id: '60', role: 'b'}]}]};
  const display = context.forceGraphData(data);
  assert.equal(display.nodes.length, 60);
  assert.equal(display.links.length, 0);
});
