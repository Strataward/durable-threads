import { createHash } from "node:crypto";
import { RISK_LEVELS, type RiskClass } from "@durable-threads/contracts";
import { classifyRisk } from "./risk.js";

export class DecisionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DecisionError";
  }
}

export type QuestionKind = "noul" | "choice" | "score";
export type DecisionGate = "auto" | "verify" | "review" | "escalate";
export type JSONState = string | Record<string, unknown> | unknown[];

export interface DecisionQuestion {
  kind: QuestionKind;
  instructions: JSONState | null;
  criteria: Record<string, JSONState | null> | JSONState[] | null;
}

export interface DecisionAnswer {
  name: string;
  kind: QuestionKind;
  value: boolean | string | number;
  certainty: number;
  probabilities: Record<string, number>;
  providerConfidence: number | null;
}

export interface DecisionBatch {
  engine: string;
  model: string;
  stateHash: string;
  answers: Record<string, DecisionAnswer>;
  usage: Record<string, number> | null;
}

export interface DecisionEngine {
  decide(input: {
    state: JSONState;
    questions: Record<string, DecisionQuestion>;
  }): Promise<DecisionBatch>;
}

export function noulQuestion(
  instructions: JSONState,
  criteria?: { true?: JSONState | null; false?: JSONState | null },
): DecisionQuestion {
  return {
    kind: "noul",
    instructions,
    criteria: criteria ? { true: criteria.true ?? null, false: criteria.false ?? null } : null,
  };
}

export function choiceQuestion(
  instructions: JSONState,
  criteria: Record<string, JSONState | null>,
): DecisionQuestion {
  if (!Object.keys(criteria).length) {
    throw new Error("choice criteria must not be empty");
  }
  return { kind: "choice", instructions, criteria: { ...criteria } };
}

export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  }
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`).join(",")}}`;
}

export function canonicalStateHash(state: JSONState): string {
  const payload = canonicalJson(state);
  return `sha256:${createHash("sha256").update(payload, "utf8").digest("hex")}`;
}

export function answerToDict(answer: DecisionAnswer): Record<string, unknown> {
  return {
    name: answer.name,
    kind: answer.kind,
    value: answer.value,
    certainty: answer.certainty,
    probabilities: { ...answer.probabilities },
    providerConfidence: answer.providerConfidence,
  };
}

export function batchToDict(batch: DecisionBatch): Record<string, unknown> {
  return {
    engine: batch.engine,
    model: batch.model,
    stateHash: batch.stateHash,
    answers: Object.fromEntries(
      Object.entries(batch.answers).map(([name, answer]) => [name, answerToDict(answer)]),
    ),
    usage: batch.usage ? { ...batch.usage } : null,
  };
}

function noulProbabilities(trueProbability: number): Record<string, number> {
  return { true: trueProbability, false: 1 - trueProbability };
}

function heuristicAnswer(
  name: string,
  question: DecisionQuestion,
  value: boolean | string,
  probabilities: Record<string, number>,
): DecisionAnswer {
  const expectedKind: QuestionKind = typeof value === "boolean" ? "noul" : "choice";
  if (question.kind !== expectedKind) {
    throw new DecisionError(
      `question '${name}' has kind '${question.kind}'; expected '${expectedKind}'`,
    );
  }
  return {
    name,
    kind: expectedKind,
    value,
    certainty: Math.max(...Object.values(probabilities)),
    probabilities,
    providerConfidence: null,
  };
}

export class HeuristicDecisionEngine implements DecisionEngine {
  constructor(
    readonly engineName = "heuristic",
    readonly model = "heuristic",
  ) {}

  async decide(input: {
    state: JSONState;
    questions: Record<string, DecisionQuestion>;
  }): Promise<DecisionBatch> {
    const answers: Record<string, DecisionAnswer> = {};
    for (const [name, question] of Object.entries(input.questions)) {
      if (
        ![
          "risk",
          "delegate",
          "ambiguous",
          "execution_shape",
          "independent_review",
          "semantic_complete",
          "evidence_sufficient",
          "intervention",
        ].includes(name)
      ) {
        throw new DecisionError(`heuristic engine does not support question: ${name}`);
      }
      if (!input.state || typeof input.state !== "object" || Array.isArray(input.state)) {
        throw new DecisionError("heuristic engine requires object state");
      }
      answers[name] = this.answer(name, question, input.state as Record<string, unknown>);
    }
    return {
      engine: this.engineName,
      model: this.model,
      stateHash: canonicalStateHash(input.state),
      answers,
      usage: null,
    };
  }

  private answer(
    name: string,
    question: DecisionQuestion,
    state: Record<string, unknown>,
  ): DecisionAnswer {
    if (name === "risk") {
      const risk = classifyRisk({
        objective: String(state.objective ?? ""),
        allowedPaths: (state.allowedPaths as string[]) ?? [],
        acceptance: (state.acceptance as string[]) ?? [],
      }).riskClass;
      const probabilities = Object.fromEntries(RISK_LEVELS.map((item) => [item, 0.025]));
      probabilities[risk] = 0.9;
      return heuristicAnswer(name, question, risk, probabilities);
    }
    if (name === "delegate") {
      const allowed = state.allowedPaths;
      const acceptance = state.acceptance;
      const probability =
        Array.isArray(allowed) && allowed.length >= 1 && Array.isArray(acceptance) && acceptance.length >= 1
          ? 0.85
          : 0.3;
      return heuristicAnswer(name, question, probability >= 0.5, noulProbabilities(probability));
    }
    if (name === "ambiguous") {
      const probability = state.acceptance ? 0.2 : 0.7;
      return heuristicAnswer(name, question, probability >= 0.5, noulProbabilities(probability));
    }
    const risk = classifyRisk({
      objective: String(state.objective ?? ""),
      allowedPaths: (state.allowedPaths as string[]) ?? [],
      acceptance: (state.acceptance as string[]) ?? [],
    }).riskClass;
    const highRisk = risk === "R3" || risk === "R4";
    if (name === "execution_shape") {
      const value = highRisk ? "worker_plus_review" : "single_worker";
      const probabilities: Record<string, number> = {
        single_worker: 0.05,
        worker_plus_review: 0.05,
        parallel_workers: 0.05,
      };
      probabilities[value] = 0.9;
      return heuristicAnswer(name, question, value, probabilities);
    }
    if (name === "independent_review") {
      const probability = highRisk ? 0.95 : 0.15;
      return heuristicAnswer(name, question, probability >= 0.5, noulProbabilities(probability));
    }
    if (name === "semantic_complete") {
      const probability = state.exitCode === 0 && Boolean(state.evidenceComplete) ? 0.9 : 0.1;
      return heuristicAnswer(name, question, probability >= 0.5, noulProbabilities(probability));
    }
    if (name === "evidence_sufficient") {
      const checks = state.checks;
      const probability =
        Boolean(state.evidenceComplete) && Array.isArray(checks) && checks.length > 0 ? 0.9 : 0.1;
      return heuristicAnswer(name, question, probability >= 0.5, noulProbabilities(probability));
    }
    const exitCode = state.exitCode;
    let value = "switch_executor";
    let probability = 0.6;
    if (exitCode === 0 && state.evidenceComplete) {
      value = "accept";
      probability = 0.9;
    } else if (exitCode === 0) {
      value = "correct_same";
      probability = 0.6;
    }
    const choices = ["accept", "correct_same", "switch_executor", "stronger_model", "human_review"];
    const remainder = (1.0 - probability) / (choices.length - 1);
    const probabilities = Object.fromEntries(choices.map((choice) => [choice, remainder]));
    probabilities[value] = probability;
    return heuristicAnswer(name, question, value, probabilities);
  }
}

export class StaticDecisionEngine implements DecisionEngine {
  constructor(
    readonly answers: Record<string, DecisionAnswer>,
    readonly engineName = "static",
    readonly model = "static",
  ) {}

  async decide(input: {
    state: JSONState;
    questions: Record<string, DecisionQuestion>;
  }): Promise<DecisionBatch> {
    const missing = Object.keys(input.questions).filter((name) => !(name in this.answers));
    if (missing.length) {
      throw new DecisionError(`static engine missing answer(s): ${missing.join(", ")}`);
    }
        return {
      engine: this.engineName,
      model: this.model,
      stateHash: canonicalStateHash(input.state),
      answers: Object.fromEntries(
        Object.keys(input.questions).map((name) => [name, this.answers[name]!]),
      ),
      usage: null,
    };
  }
}

export class JevDecisionEngine implements DecisionEngine {
  constructor(
    readonly model = "jev-latest",
    readonly apiKey: string | null = null,
    readonly baseUrl: string | null = null,
    readonly timeoutSeconds = 30,
  ) {
    if (!model.trim()) {
      throw new Error("model must be a non-empty string");
    }
    if (timeoutSeconds <= 0) {
      throw new Error("timeout_seconds must be > 0");
    }
  }

  async decide(input: {
    state: JSONState;
    questions: Record<string, DecisionQuestion>;
  }): Promise<DecisionBatch> {
    if (!Object.keys(input.questions).length) {
      throw new DecisionError("questions must not be empty");
    }
    const wireQuestions: Record<string, unknown> = {};
    for (const [name, question] of Object.entries(input.questions)) {
      if (!name) {
        throw new DecisionError("question names must be non-empty strings");
      }
      if (question.kind === "noul") {
        wireQuestions[name] = {
          type: "noul",
          instructions: question.instructions,
          criteria: question.criteria,
        };
      } else if (question.kind === "choice") {
        if (!question.criteria || Array.isArray(question.criteria) || !Object.keys(question.criteria).length) {
          throw new DecisionError(`choice question '${name}' requires mapping criteria`);
        }
        wireQuestions[name] = {
          type: "choice",
          instructions: question.instructions,
          criteria: question.criteria,
        };
      } else if (question.kind === "score") {
        if (!Array.isArray(question.criteria) || !question.criteria.length) {
          throw new DecisionError(`score question '${name}' requires ordered criteria`);
        }
        wireQuestions[name] = {
          type: "score",
          instructions: question.instructions,
          criteria: question.criteria,
        };
      }
    }
    const url = `${(this.baseUrl ?? "https://api.typesafe.ai").replace(/\/$/, "")}/v1/systemone`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutSeconds * 1000);
    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(this.apiKey ? { authorization: `Bearer ${this.apiKey}` } : {}),
        },
        body: JSON.stringify({
          model: this.model,
          state: input.state,
          questions: wireQuestions,
        }),
        signal: controller.signal,
      });
    } catch (error) {
      throw new DecisionError(`Jev request failed: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      clearTimeout(timer);
    }
    if (!response.ok) {
      throw new DecisionError(`Jev request failed with status ${response.status}`);
    }
    const payload = (await response.json()) as {
      model?: string;
      answers?: Record<string, Record<string, unknown>>;
      usage?: { input_tokens?: number; output_tokens?: number; inputTokens?: number; outputTokens?: number };
    };
    const answers: Record<string, DecisionAnswer> = {};
    for (const [name, answer] of Object.entries(payload.answers ?? {})) {
      const answerType = String(answer.type ?? "");
      if (answerType === "noul") {
        const probability = Number(answer.noul);
        answers[name] = {
          name,
          kind: "noul",
          value: probability >= 0.5,
          certainty: Math.max(probability, 1 - probability),
          probabilities: { true: probability, false: 1 - probability },
          providerConfidence: null,
        };
      } else if (answerType === "choice") {
        const probabilities = Object.fromEntries(
          Object.entries((answer.probabilities as Record<string, number>) ?? {}).map(([key, value]) => [
            String(key),
            Number(value),
          ]),
        );
        answers[name] = {
          name,
          kind: "choice",
          value: String(answer.choice),
          certainty: Object.values(probabilities).length ? Math.max(...Object.values(probabilities)) : 0,
          probabilities,
          providerConfidence: answer.confidence === undefined ? null : Number(answer.confidence),
        };
      } else if (answerType === "score") {
        const probabilities = Object.fromEntries(
          Object.entries((answer.probabilities as Record<string, number>) ?? {}).map(([key, value]) => [
            String(key),
            Number(value),
          ]),
        );
        answers[name] = {
          name,
          kind: "score",
          value: Number(answer.score),
          certainty: Number(answer.confidence),
          probabilities,
          providerConfidence: Number(answer.confidence),
        };
      } else {
        throw new DecisionError(`unsupported Jev answer type for '${name}': '${answerType}'`);
      }
    }
    const usage: Record<string, number> = {};
    const inputTokens = payload.usage?.inputTokens ?? payload.usage?.input_tokens;
    const outputTokens = payload.usage?.outputTokens ?? payload.usage?.output_tokens;
    if (typeof inputTokens === "number") {
      usage.inputTokens = inputTokens;
    }
    if (typeof outputTokens === "number") {
      usage.outputTokens = outputTokens;
    }
    return {
      engine: "typesafe:system-one",
      model: payload.model ?? this.model,
      stateHash: canonicalStateHash(input.state),
      answers,
      usage: Object.keys(usage).length ? usage : null,
    };
  }
}

export class DecisionPolicy {
  constructor(
    readonly escalateBelow = 0.6,
    readonly reviewBelow = 0.8,
    readonly autoThresholdR0 = 0.7,
    readonly autoThresholdR1 = 0.85,
    readonly autoThresholdR2 = 0.9,
    readonly autoThresholdR3 = 0.97,
    readonly autoThresholdR4 = 1.0,
  ) {}

  thresholdFor(riskClass: string): number {
    const values: Record<RiskClass, number> = {
      R0: this.autoThresholdR0,
      R1: this.autoThresholdR1,
      R2: this.autoThresholdR2,
      R3: this.autoThresholdR3,
      R4: this.autoThresholdR4,
    };
    const risk = riskClass.toUpperCase() as RiskClass;
    if (!(risk in values)) {
      throw new Error("risk_class must be one of R0, R1, R2, R3, R4");
    }
    return values[risk];
  }

  gate(input: { certainty: number; riskClass: string }): DecisionGate {
    if (input.certainty < 0 || input.certainty > 1) {
      throw new Error("certainty must be between 0 and 1");
    }
    const risk = input.riskClass.toUpperCase();
    const threshold = this.thresholdFor(risk);
    if (input.certainty < this.escalateBelow) {
      return "escalate";
    }
    if (risk === "R3" || risk === "R4") {
      return "review";
    }
    if (input.certainty < this.reviewBelow) {
      return "review";
    }
    if (input.certainty < threshold) {
      return "verify";
    }
    return risk === "R0" ? "auto" : "verify";
  }
}

export function decisionEngineFromEnv(
  environ: Record<string, string | undefined> = process.env,
): DecisionEngine {
  const configured = environ.DURABLE_THREADS_DECISION_ENGINE;
  const engineName = configured || (environ.TYPESAFE_API_KEY ? "jev" : "heuristic");
  if (engineName === "heuristic") {
    return new HeuristicDecisionEngine();
  }
  if (engineName === "jev") {
    return new JevDecisionEngine(
      environ.DURABLE_THREADS_JEV_MODEL ?? "jev-latest",
      environ.TYPESAFE_API_KEY || null,
      environ.TYPESAFE_BASE_URL || null,
      Number(environ.DURABLE_THREADS_JEV_TIMEOUT_SECONDS ?? "30"),
    );
  }
  throw new Error("DURABLE_THREADS_DECISION_ENGINE must be one of: jev, heuristic");
}
