import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { advise, auditUsage, probe, quotaStatus } from '../plugins/durable-threads/skills/durable-threads/scripts/pro5.mjs';

const rates = (usedPercent = 20, secondary = null) => ({ rateLimits: {
  limitId: 'codex', primary: { usedPercent, windowDurationMins: 300, resetsAt: 5000 }, secondary,
} });
const state = (patch = {}) => ({ authMode: 'chatgpt', writerState: 'known', risk: 'R1', phase: 'implement',
  currentEffort: 'medium', supportedEfforts: ['low', 'medium', 'high'], generations: 1,
  noProgressGenerations: 0, repeatedFailures: 0, elapsedSeconds: 10, stepsSinceChange: 2,
  resolvedCheckpoints: 2, observedAt: 990, rateLimits: rates(), ...patch });

test('unknown and expired quotas never become unlimited', () => {
  assert.equal(quotaStatus({}, 1000).status, 'unknown');
  assert.equal(quotaStatus(rates(), 6000).status, 'unknown');
});
test('secondary window, not only the five-hour window, binds', () => {
  const q = quotaStatus(rates(10, { usedPercent: 96, windowDurationMins: 10080, resetsAt: 5000 }), 1000);
  assert.equal(q.status, 'reserve'); assert.equal(q.remainingPercent, 4);
});
test('actual exhausted and backend spend restrictions stop new work', () => {
  assert.equal(quotaStatus(rates(100), 1000).status, 'exhausted');
  const p = rates(); p.rateLimits.rateLimitReachedType = 'workspaceOwnerUsageLimitReached';
  assert.equal(quotaStatus(p, 1000).status, 'exhausted');
});
test('quota mapping prefers the explicit relevant bucket', () => {
  const p = rates(100); p.rateLimitsByLimitId = { codex: rates(25).rateLimits };
  assert.equal(quotaStatus(p, 1000).remainingPercent, 75);
  assert.equal(quotaStatus(p, 1000, { limitId: 'other' }).status, 'unknown');
});
for (const value of [NaN, Infinity, -1, 101, '20']) {
  test(`rejects invalid percentage ${String(value)}`, () => assert.equal(quotaStatus(rates(value), 1000).status, 'unknown'));
}
test('Astra preference uses effort, not a silent model switch', () => {
  const p = advise(state(), 1000);
  assert.equal(p.action, 'set_effort'); assert.equal(p.effort, 'low'); assert.equal(p.liveControl, false);
});
test('escalation is evidence-based and constrained to advertised levels', () => {
  assert.equal(advise(state({ conceptualFailure: true }), 1000).effort, 'high');
  assert.equal(advise(state({ conceptualFailure: true, supportedEfforts: ['low', 'medium'] }), 1000).action, 'inspect_capabilities');
});
test('downshift hysteresis prevents oscillation', () => {
  assert.equal(advise(state({ stepsSinceChange: 1 }), 1000).action, 'keep');
  assert.equal(advise(state({ resolvedCheckpoints: 1 }), 1000).action, 'keep');
});
test('human approval and confident completion cannot override failed checks', () => {
  const p = advise(state({ candidateComplete: true, humanApproved: true, checksPassed: false, scopeVerified: true }), 1000);
  assert.equal(p.action, 'verify');
});
test('required review survives successful implementation', () => {
  assert.equal(advise(state({ candidateComplete: true, checksPassed: true, scopeVerified: true, risk: 'R3' }), 1000).action, 'review');
  assert.equal(advise(state({ candidateComplete: true, checksPassed: true, scopeVerified: true, reviewRequired: true }), 1000).action, 'review');
});
test('complete means stop optional verification loops', () => {
  assert.equal(advise(state({ candidateComplete: true, checksPassed: true, scopeVerified: true }), 1000).action, 'complete');
});
test('wait does not request a model and stale snapshots need refresh', () => {
  assert.equal(advise(state({ phase: 'waiting' }), 1000).action, 'wait');
  assert.equal(advise(state({ observedAt: 1 }), 1000).action, 'refresh_quota');
});
for (const patch of [{ generations: 60 }, { repeatedFailures: 2 }, { noProgressGenerations: 4 }, { elapsedSeconds: 1800 }]) {
  test(`circuit breaker ${Object.keys(patch)[0]}`, () => assert.equal(advise(state(patch), 1000).action, 'pause'));
}
test('quota reserve cannot silently reduce review or scope obligations', () => {
  assert.equal(advise(state({ rateLimits: rates(95), risk: 'R3' }), 1000).action, 'pause');
});
test('auth, cancellation and unknown writers stop even apparently completed work', () => {
  for (const patch of [{ authMode: 'apiKey' }, { writerState: 'unknown' }, { cancelled: true }]) {
    assert.equal(advise(state({ candidateComplete: true, checksPassed: true, scopeVerified: true, ...patch }), 1000).action, 'stop');
  }
});
test('invalid policy counters and boolean strings do not get coerced', () => {
  assert.throws(() => advise(state({ generations: NaN }), 1000));
  assert.throws(() => advise(state({ checksPassed: 'true' }), 1000));
});
const usage = (id = 'resp_a', extra = {}) => ({ type: 'token_usage_record', payload: {
  thread_id: 'thread_test', response_id: id,
  usage: { input_tokens: 100, cached_input_tokens: 80, output_tokens: 10, reasoning_output_tokens: 6, cache_write_input_tokens: 0, ...extra },
  thread_token_usage: { input_tokens: 999999 },
} });
async function withLog(text, fn) {
  const dir = await mkdtemp(join(tmpdir(), 'dt-pro5-test-')); const path = join(dir, 'sample.jsonl');
  try { await writeFile(path, text); return await fn(path); } finally { await rm(dir, { recursive: true, force: true }); }
}
test('usage deduplicates response IDs and ignores cumulative and nested mirrors', async () => {
  const rows = [usage(), usage(), usage('resp_b'), { type: 'event_msg', payload: { type: 'token_count', info: { total_token_usage: { input_tokens: 90000 } } } }, { type: 'compacted', payload: { latest_token_usage_record: usage().payload } }];
  await withLog(rows.map(JSON.stringify).join('\n') + '\n', async path => {
    const p = await auditUsage([path]);
    assert.equal(p.observedResponses, 2); assert.equal(p.inputTokens, 200);
    assert.equal(p.inputPlusOutputTokens, 220); assert.equal(p.reasoningOutputTokens, 12);
    assert.equal(p.coverage.duplicates, 1); assert.equal(p.coverage.ignored, 2);
    assert.equal(p.billingEstimate, null); assert.ok(!JSON.stringify(p).includes('thread_test'));
  });
});
test('partial and unsupported logs expose coverage, not fabricated zero costs', async () => {
  await withLog('{bad}\n' + JSON.stringify(usage('resp_bad', { input_tokens: -5 })) + '\n{"type":', async path => {
    const p = await auditUsage([path]);
    assert.equal(p.coverage.malformed, 1); assert.equal(p.coverage.invalidUsage, 1);
    assert.equal(p.coverage.tailFragments, 1); assert.equal(p.observedResponses, 0);
    assert.equal(p.cachedInputRatio, null);
  });
});
test('conflicting duplicate receipts are surfaced and never added twice', async () => {
  await withLog([usage(), usage('resp_a', { input_tokens: 120 })].map(JSON.stringify).join('\n') + '\n', async path => {
    const p = await auditUsage([path]); assert.equal(p.inputTokens, 100); assert.equal(p.coverage.conflictingDuplicates, 1);
  });
});
test('bounded audit drops oversized lines and rejects too-large samples', async () => {
  await withLog('x'.repeat(500) + '\n' + JSON.stringify(usage()) + '\n', async path => {
    const p = await auditUsage([path], { maxLineBytes: 400 }); assert.equal(p.coverage.oversized, 1); assert.equal(p.observedResponses, 1);
    await assert.rejects(auditUsage([path], { maxBytes: 100 }));
  });
});
const fakeServer = `
const readline = require('node:readline');
readline.createInterface({input:process.stdin}).on('line', line => {
  const r = JSON.parse(line); if (r.method === 'initialized') return;
  let result;
  if (r.method === 'initialize') result = {userAgent:'fake'};
  else if (r.method === 'account/read') result = {account:{type:'chatgpt',planType:'pro',email:'private@example.test',accessToken:'PRIVATE_VALUE_TEST'}};
  else if (r.method === 'account/rateLimits/read') result = {rateLimits:{limitId:'codex',primary:{usedPercent:20,windowDurationMins:300,resetsAt:Math.floor(Date.now()/1000)+10000},secondary:null}};
  else if (r.method === 'model/list') result = r.params.cursor ? {data:[{model:'model_b',supportedReasoningEfforts:[{reasoningEffort:'high'}]}],nextCursor:null} : {data:[{model:'model_a',defaultReasoningEffort:'medium',supportedReasoningEfforts:[{reasoningEffort:'low'},{reasoningEffort:'medium'}]}],nextCursor:'next'};
  else if (r.method === 'experimentalFeature/list') result = {data:[{name:'step_model_switching',enabled:true}],nextCursor:null};
  else { process.exit(23); return; }
  console.log(JSON.stringify({id:r.id,result}));
});`;
test('probe only reads metadata, follows pages and strips credentials', async () => {
  const p = await probe({ command: process.execPath, args: ['-e', fakeServer] });
  assert.equal(p.models.length, 2); assert.equal(p.modelCatalogComplete, true);
  assert.equal(p.authMode, 'chatgpt'); assert.equal(p.planMultiplierVerified, false);
  assert.equal(p.liveStepControlVerified, false); assert.equal(p.quota.status, 'available');
  assert.ok(!JSON.stringify(p).includes('PRIVATE_VALUE_TEST')); assert.ok(!JSON.stringify(p).includes('@'));
});
test('probe reports incomplete pagination rather than returning complete capabilities', async () => {
  const broken = fakeServer.replace("r.params.cursor ?", "false ?");
  const p = await probe({ command: process.execPath, args: ['-e', broken] });
  assert.equal(p.modelCatalogComplete, false);
});
test('probe timeout and missing binaries fail boundedly', async () => {
  await assert.rejects(probe({ command: process.execPath, args: ['-e', 'setInterval(()=>{},1000)'], timeoutMs: 100 }));
  await assert.rejects(probe({ command: 'dt-test-nonexistent-executable', timeoutMs: 100 }));
});
