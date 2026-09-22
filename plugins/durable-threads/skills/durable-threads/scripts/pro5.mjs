#!/usr/bin/env node
/** Local Pro-allowance diagnostics. No model turns, config writes, or quota resets. */
import { spawn } from 'node:child_process';
import { createReadStream, readFileSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

const record = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const body = (v) => record(v?.result) ? v.result : v;
const count = (v) => Number.isSafeInteger(v) && v >= 0;
const finite = (v) => typeof v === 'number' && Number.isFinite(v);
const identifier = (v) => typeof v === 'string' && /^[a-zA-Z0-9_.:/-]{1,128}$/.test(v);
const hash = (v) => createHash('sha256').update(v).digest('hex');
const META_METHODS = new Set(['initialize', 'account/read', 'account/rateLimits/read', 'model/list', 'experimentalFeature/list']);

/** A Pro plan label does not establish the 5x/20x entitlement. Missing != unlimited. */
export function quotaStatus(payload, nowSeconds, { limitId = 'codex', reservePercent = 10 } = {}) {
  if (!finite(nowSeconds) || nowSeconds < 0 || !finite(reservePercent) || reservePercent < 0 || reservePercent >= 100) {
    throw new Error('Invalid quota policy');
  }
  const p = body(payload);
  const snapshot = p?.rateLimitsByLimitId?.[limitId] ??
    (p?.rateLimits?.limitId === limitId ? p.rateLimits : null);
  if (!record(snapshot)) return { status: 'unknown', limitId, windows: [], reason: 'No matching allowance bucket' };
  const windows = [];
  let missing = false;
  for (const name of ['primary', 'secondary']) {
    const w = snapshot[name];
    if (w == null) continue;
    if (!record(w) || !finite(w.usedPercent) || w.usedPercent < 0 || w.usedPercent > 100 ||
        !count(w.resetsAt) || !count(w.windowDurationMins) || w.windowDurationMins === 0) {
      missing = true;
      continue;
    }
    windows.push({ name, usedPercent: w.usedPercent, remainingPercent: 100 - w.usedPercent,
      durationMinutes: w.windowDurationMins, resetsAt: w.resetsAt });
  }
  // A past reset is a reason to refresh, never permission to assume a fresh allowance.
  if (!windows.length || missing || windows.some(w => w.resetsAt <= nowSeconds)) {
    return { status: 'unknown', limitId, windows, reason: 'Missing, invalid, or expired window; refresh /status' };
  }
  if (snapshot.rateLimitReachedType != null || snapshot.spendControlReached === true ||
      windows.some(w => w.remainingPercent <= 0)) {
    return { status: 'exhausted', limitId, windows, reason: 'Stop new model work; retain a handoff' };
  }
  const remainingPercent = Math.min(...windows.map(w => w.remainingPercent));
  return { status: remainingPercent <= reservePercent ? 'reserve' : 'available', limitId,
    windows, remainingPercent, reason: 'Observed bucket only; not a token-to-quota estimate' };
}

/** Pure advisory governor. The plugin cannot intercept Codex inference or enforce account limits. */
export function advise(state, nowSeconds) {
  if (!record(state) || !finite(nowSeconds)) throw new Error('Expected an explicit state object and time');
  for (const key of ['cancelled', 'reviewRequired', 'reviewPassed', 'candidateComplete', 'checksPassed', 'scopeVerified', 'humanApproved', 'conceptualFailure', 'unresolvedCritical']) {
    if (key in state && typeof state[key] !== 'boolean') throw new Error(`Invalid flag: ${key}`);
  }
  const reply = (action, reason, effort = state.currentEffort ?? null) => ({
    action, reason, effort, advisoryOnly: true, scope: 'next-safe-boundary', liveControl: false,
  });
  if (state.cancelled === true) return reply('stop', 'Cancellation remains authoritative');
  if (state.authMode !== 'chatgpt') return reply('stop', 'Verify ChatGPT sign-in; do not fall back to paid API billing');
  if (state.writerState !== 'known') return reply('stop', 'Reconcile writer state before retrying');
  if (!['R0', 'R1', 'R2', 'R3', 'R4'].includes(state.risk)) throw new Error('Invalid risk class');
  const reviewRequired = state.reviewRequired === true || ['R3', 'R4'].includes(state.risk);
  if (state.candidateComplete === true && state.checksPassed === true && state.scopeVerified === true) {
    return reviewRequired && state.reviewPassed !== true
      ? reply('review', 'Independent review is still required')
      : reply('complete', 'Acceptance passed; stop without optional repeat reviews');
  }
  for (const key of ['generations', 'noProgressGenerations', 'repeatedFailures', 'elapsedSeconds', 'stepsSinceChange', 'resolvedCheckpoints']) {
    if (!count(state[key])) throw new Error(`Missing or invalid counter: ${key}`);
  }
  // These are DT experiment defaults, not the subscription's rate limits.
  if (state.generations >= 60 || state.elapsedSeconds >= 1800 ||
      state.noProgressGenerations >= 4 || state.repeatedFailures >= 2) {
    return reply('pause', 'Bounded run/circuit-breaker reached; diagnose or revise the contract');
  }
  if (!finite(state.observedAt) || state.observedAt > nowSeconds || nowSeconds - state.observedAt > 300) {
    return reply('refresh_quota', 'Allowance observation is missing or stale');
  }
  const quota = quotaStatus(state.rateLimits, nowSeconds, { limitId: state.limitId ?? 'codex' });
  if (quota.status === 'unknown') return reply('refresh_quota', quota.reason);
  if (quota.status === 'exhausted' || quota.status === 'reserve') return reply('pause', 'Preserve quota and required verification; do not silently weaken acceptance');
  if (state.risk === 'R4' && state.humanApproved !== true) return reply('review', 'Systemic work needs approval before execution');
  if (state.phase === 'waiting') return reply('wait', 'Use the existing native wait/event mechanism, not another inference');
  if (state.candidateComplete === true) return reply('verify', 'A completion claim or human approval cannot replace passing checks and scope evidence');
  if (!['read', 'implement', 'diagnose', 'review'].includes(state.phase)) throw new Error('Invalid work phase');
  const levels = ['low', 'medium', 'high', 'xhigh', 'max'];
  const supported = state.supportedEfforts;
  if (!Array.isArray(supported) || !supported.length || !supported.every(x => typeof x === 'string') ||
      !supported.includes(state.currentEffort) || !levels.includes(state.currentEffort)) {
    return reply('inspect_capabilities', 'Use live advertised effort levels; never invent a universal effort ladder');
  }
  let desired = state.phase === 'diagnose' || state.phase === 'review' || reviewRequired ? 'medium' : 'low';
  if (state.conceptualFailure === true || state.unresolvedCritical === true) desired = 'high';
  const target = levels.find(x => levels.indexOf(x) >= levels.indexOf(desired) &&
    levels.indexOf(x) <= 2 && supported.includes(x));
  if (!target) return reply('inspect_capabilities', 'No supported effort within the automatic high-effort cap');
  const down = levels.indexOf(target) < levels.indexOf(state.currentEffort);
  if (down && (state.stepsSinceChange < 2 || state.resolvedCheckpoints < 2 || state.unresolvedCritical === true)) {
    return reply('keep', 'Downshift requires two resolved checkpoints and a two-step cooldown');
  }
  return reply(target === state.currentEffort ? 'keep' : 'set_effort',
    'Same explicitly selected model; validate quality after the next bounded work unit', target);
}

/** Read only explicitly selected rollouts. Ignore cumulative mirrors and nested compaction copies. */
export async function auditUsage(paths, { maxBytes = 256 * 1024 * 1024, maxLineBytes = 4 * 1024 * 1024 } = {}) {
  if (!Array.isArray(paths) || !paths.length || !paths.every(p => typeof p === 'string') ||
      !count(maxBytes) || maxBytes === 0 || !count(maxLineBytes) || maxLineBytes === 0) throw new Error('Invalid audit input');
  const seen = new Map();
  const totals = { inputTokens: 0, cachedInputTokens: 0, outputTokens: 0, reasoningOutputTokens: 0, cacheWriteInputTokens: 0 };
  const coverage = { lines: 0, ignored: 0, malformed: 0, oversized: 0, invalidUsage: 0,
    unidentified: 0, duplicates: 0, conflictingDuplicates: 0, missingOptional: 0, tailFragments: 0 };
  let responses = 0;
  const consume = (line) => {
    coverage.lines++;
    let row;
    try { row = JSON.parse(line); } catch { coverage.malformed++; return; }
    if (row?.type !== 'token_usage_record') { coverage.ignored++; return; }
    const p = row.payload;
    if (!record(p) || !identifier(p.response_id) || !identifier(p.thread_id)) { coverage.unidentified++; return; }
    const u = p.usage;
    if (!record(u) || ![u.input_tokens, u.cached_input_tokens, u.output_tokens].every(count) ||
        u.cached_input_tokens > u.input_tokens ||
        (u.reasoning_output_tokens != null && (!count(u.reasoning_output_tokens) || u.reasoning_output_tokens > u.output_tokens)) ||
        (u.cache_write_input_tokens != null && (!count(u.cache_write_input_tokens) || u.cache_write_input_tokens > u.input_tokens))) {
      coverage.invalidUsage++; return;
    }
    const values = [u.input_tokens, u.cached_input_tokens, u.output_tokens, u.reasoning_output_tokens ?? 0, u.cache_write_input_tokens ?? 0];
    const key = hash(`${p.thread_id}\0${p.response_id}`);
    const signature = values.join(',');
    if (seen.has(key)) {
      coverage.duplicates++;
      if (seen.get(key) !== signature) coverage.conflictingDuplicates++;
      return;
    }
    const keys = Object.keys(totals);
    if (keys.some((k, i) => !Number.isSafeInteger(totals[k] + values[i])) ||
        !Number.isSafeInteger(totals.inputTokens + values[0] + totals.outputTokens + values[2])) throw new Error('Usage total exceeds safe integer range');
    seen.set(key, signature);
    responses++;
    if (u.reasoning_output_tokens == null || u.cache_write_input_tokens == null) coverage.missingOptional++;
    keys.forEach((k, i) => { totals[k] += values[i]; });
  };
  let bytes = 0;
  for (const path of paths) {
    let pending = Buffer.alloc(0);
    let dropping = false;
    for await (const chunk of createReadStream(path, { highWaterMark: 64 * 1024 })) {
      bytes += chunk.length;
      if (bytes > maxBytes) throw new Error('Audit byte budget exceeded; select a smaller explicit sample');
      const joined = Buffer.concat([pending, chunk]);
      let start = 0;
      for (let i = 0; i < joined.length; i++) {
        if (joined[i] !== 10) continue;
        if (dropping) dropping = false;
        else if (i - start > maxLineBytes) coverage.oversized++;
        else if (i > start) consume(joined.subarray(start, i).toString('utf8'));
        start = i + 1;
      }
      pending = joined.subarray(start);
      if (pending.length > maxLineBytes) {
        if (!dropping) coverage.oversized++;
        dropping = true;
        pending = Buffer.alloc(0);
      }
    }
    if (pending.length || dropping) coverage.tailFragments++; // Active writers can leave an incomplete final line.
  }
  return { schemaVersion: 1, observedResponses: responses, ...totals,
    uncachedInputTokens: totals.inputTokens - totals.cachedInputTokens,
    inputPlusOutputTokens: totals.inputTokens + totals.outputTokens,
    cachedInputRatio: totals.inputTokens ? totals.cachedInputTokens / totals.inputTokens : null,
    coverage, billingEstimate: null, remainingAllowanceEstimate: null,
    caveat: 'Completed response records in selected files only. Reasoning is a subset of output. Warmups, compactions, children, and other products may be missing. No billing or quota inference.' };
}

/** Metadata-only stdio transport; method allowlist prevents accidental model execution. */
export async function probe({ command = 'codex', args = ['app-server'], timeoutMs = 10000 } = {}) {
  if (!count(timeoutMs) || timeoutMs < 100 || timeoutMs > 60000) throw new Error('Invalid probe timeout');
  const child = spawn(command, args, { stdio: ['pipe', 'pipe', 'pipe'], shell: false });
  child.stdout.setEncoding('utf8');
  child.stderr.resume(); // Never echo raw server errors/config/credentials.
  const pending = new Map();
  const errors = [];
  let seq = 0;
  let buffer = '';
  let fatal = false;
  const fail = () => {
    fatal = true;
    for (const p of pending.values()) { clearTimeout(p.timer); p.reject(new Error('Metadata transport failed')); }
    pending.clear();
  };
  child.on('error', fail);
  child.on('exit', fail);
  child.stdin.on('error', fail);
  child.stdout.on('data', chunk => {
    buffer += chunk.toString('utf8');
    if (Buffer.byteLength(buffer) > 8 * 1024 * 1024) { fail(); child.kill(); return; }
    let newline;
    while ((newline = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newline); buffer = buffer.slice(newline + 1);
      let message;
      try { message = JSON.parse(line); } catch { continue; }
      if (message.method && message.id !== undefined) {
        // Fail closed on unexpected server requests rather than approve tools or login.
        child.stdin.write(JSON.stringify({ id: message.id, error: { code: -32601, message: 'Metadata-only client' } }) + '\n');
        continue;
      }
      const p = pending.get(message.id);
      if (!p) continue;
      clearTimeout(p.timer); pending.delete(message.id);
      if (message.error) p.reject(new Error('Metadata method unavailable'));
      else p.resolve(message.result);
    }
  });
  const request = (method, params) => {
    if (!META_METHODS.has(method) || fatal) return Promise.reject(new Error('Metadata transport unavailable'));
    return new Promise((resolve, reject) => {
      const id = ++seq;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error('Metadata timeout')); }, timeoutMs);
      pending.set(id, { resolve, reject, timer });
      child.stdin.write(JSON.stringify({ id, method, params }) + '\n');
    });
  };
  const safe = async (method, params) => {
    try { return await request(method, params); } catch { errors.push(method); return null; }
  };
  const page = async (method, extra) => {
    const data = []; const cursors = new Set(); let cursor;
    for (let i = 0; i < 20; i++) {
      const p = await safe(method, { ...extra, limit: 100, ...(cursor ? { cursor } : {}) });
      if (!Array.isArray(p?.data)) return { data, complete: false };
      data.push(...p.data);
      if (p.nextCursor == null) return { data, complete: true };
      if (typeof p.nextCursor !== 'string' || !p.nextCursor || cursors.has(p.nextCursor)) return { data, complete: false };
      cursor = p.nextCursor; cursors.add(cursor);
    }
    return { data, complete: false };
  };
  try {
    const initialized = await safe('initialize', { clientInfo: { name: 'durable_threads_pro5', version: '0.1.0' }, capabilities: { experimentalApi: false } });
    if (initialized == null) throw new Error('Codex metadata initialization failed');
    child.stdin.write(JSON.stringify({ method: 'initialized', params: {} }) + '\n');
    const account = await safe('account/read', { refreshToken: false });
    const rates = await safe('account/rateLimits/read', {});
    const models = await page('model/list', { includeHidden: false });
    const features = await page('experimentalFeature/list', {});
    const now = Math.floor(Date.now() / 1000);
    return {
      schemaVersion: 1, observedAt: now, requestedProfile: 'pro5-astra', planMultiplierVerified: false,
      authMode: account?.account?.type === 'chatgpt' ? 'chatgpt' : account?.account?.type === 'apiKey' ? 'apiKey' : 'unknown',
      planType: ['pro', 'plus', 'free', 'team', 'business', 'enterprise', 'edu'].includes(account?.account?.planType) ? account.account.planType : 'unknown',
      quota: quotaStatus(rates, now),
      quotaBuckets: Object.keys(rates?.rateLimitsByLimitId ?? {}).filter(identifier).map(limitId => quotaStatus(rates, now, { limitId })),
      modelCatalogComplete: models.complete,
      models: models.data.filter(m => identifier(m?.model ?? m?.id)).map(m => ({
        model: m.model ?? m.id,
        supportedEfforts: Array.isArray(m.supportedReasoningEfforts) ? m.supportedReasoningEfforts.map(e => e?.reasoningEffort).filter(identifier) : [],
        defaultEffort: identifier(m.defaultReasoningEffort) ? m.defaultReasoningEffort : null,
      })),
      featureCatalogComplete: features.complete,
      experimentalFeatures: features.data.filter(f => ['step_model_switching', 'reasoning_effort_override'].includes(f?.name)).map(f => ({ name: f.name, enabled: f.enabled === true })),
      errors: [...new Set(errors)], liveStepControlVerified: false,
    };
  } finally {
    fail(); child.stdin.end(); child.kill('SIGTERM');
    const timer = setTimeout(() => child.kill('SIGKILL'), 1000); timer.unref();
    if (child.exitCode === null && child.signalCode === null) await new Promise(resolve => {
      child.once('exit', resolve); child.once('error', resolve);
      const fallback = setTimeout(resolve, 1500); fallback.unref();
    });
    clearTimeout(timer);
  }
}

async function main(argv) {
  const [command, ...paths] = argv;
  if (command === 'probe' && paths.length === 0) return probe();
  if (command === 'audit' && paths.length) return auditUsage(paths);
  if (command === 'advise' && paths.length === 1) {
    if (statSync(paths[0]).size > 1024 * 1024) throw new Error('State file is too large');
    const raw = readFileSync(paths[0]);
    if (raw.length > 1024 * 1024) throw new Error('State file is too large');
    return advise(JSON.parse(raw), Math.floor(Date.now() / 1000));
  }
  throw new Error('Usage: node pro5.mjs probe | audit <explicit-rollout.jsonl> [...] | advise <state.json>');
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main(process.argv.slice(2)).then(value => console.log(JSON.stringify(value, null, 2))).catch(error => {
    // Never expose local paths, transcript excerpts, or server error bodies.
    console.error(error.message.startsWith('Usage:') ? error.message : 'Pro5 diagnostic failed. Check inputs, installed Codex, and local permissions. No settings were changed.');
    process.exitCode = 1;
  });
}
