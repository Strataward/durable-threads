import type { TaskRecord, TaskRunResult, TaskStatus } from "@durable-threads/contracts";

export interface TaskStore {
  create(record: TaskRecord): Promise<void>;
  get(id: string): Promise<TaskRecord | null>;
  list(): Promise<TaskRecord[]>;
  update(
    id: string,
    patch: Partial<Pick<TaskRecord, "status" | "risk" | "phase" | "reviewPending" | "result">>,
  ): Promise<TaskRecord>;
}

export function now(): string {
  return new Date().toISOString();
}

export function newTask(input: {
  id: string;
  workflowId: string;
  objective: string;
}): TaskRecord {
  const timestamp = now();
  return {
    id: input.id,
    workflowId: input.workflowId,
    objective: input.objective,
    status: "created",
    risk: null,
    phase: "created",
    reviewPending: false,
    result: null,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
}

export class MemoryTaskStore implements TaskStore {
  private readonly tasks = new Map<string, TaskRecord>();

  async create(record: TaskRecord): Promise<void> {
    this.tasks.set(record.id, record);
  }

  async get(id: string): Promise<TaskRecord | null> {
    return this.tasks.get(id) ?? null;
  }

  async list(): Promise<TaskRecord[]> {
    return [...this.tasks.values()].sort((left, right) => right.createdAt.localeCompare(left.createdAt));
  }

  async update(
    id: string,
    patch: Partial<Pick<TaskRecord, "status" | "risk" | "phase" | "reviewPending" | "result">>,
  ): Promise<TaskRecord> {
    const current = this.tasks.get(id);
    if (!current) {
      throw new Error(`task not found: ${id}`);
    }
    const next = { ...current, ...patch, updatedAt: now() };
    this.tasks.set(id, next);
    return next;
  }
}

export function applyResult(result: TaskRunResult): Pick<TaskRecord, "status" | "risk" | "phase" | "reviewPending" | "result"> {
  return {
    status: result.status as TaskStatus,
    risk: result.finalRisk,
    phase: result.status,
    reviewPending: result.status === "review_required",
    result,
  };
}
