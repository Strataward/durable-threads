import pg from "pg";
import type { TaskRecord } from "@durable-threads/contracts";
import type { TaskStore } from "./store.js";
import { now } from "./store.js";

const SCHEMA = `
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  workflow_id TEXT NOT NULL UNIQUE,
  objective TEXT NOT NULL,
  status TEXT NOT NULL,
  risk TEXT,
  phase TEXT NOT NULL,
  review_pending BOOLEAN NOT NULL DEFAULT FALSE,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
`;

function rowToTask(row: pg.QueryResultRow): TaskRecord {
  const payload = row.payload ?? {};
  return {
    id: row.id,
    workflowId: row.workflow_id,
    objective: row.objective,
    status: row.status,
    risk: row.risk,
    phase: row.phase,
    reviewPending: row.review_pending,
    result: payload.result ?? null,
    createdAt: new Date(row.created_at).toISOString(),
    updatedAt: new Date(row.updated_at).toISOString(),
  };
}

export class PostgresTaskStore implements TaskStore {
  constructor(private readonly pool: pg.Pool) {}

  static async connect(url: string): Promise<PostgresTaskStore> {
    const pool = new pg.Pool({ connectionString: url });
    await pool.query(SCHEMA);
    return new PostgresTaskStore(pool);
  }

  async create(record: TaskRecord): Promise<void> {
    await this.pool.query(
      `INSERT INTO tasks (id, workflow_id, objective, status, risk, phase, review_pending, payload, created_at, updated_at)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
      [
        record.id,
        record.workflowId,
        record.objective,
        record.status,
        record.risk,
        record.phase,
        record.reviewPending,
        { result: record.result },
        record.createdAt,
        record.updatedAt,
      ],
    );
  }

  async get(id: string): Promise<TaskRecord | null> {
    const result = await this.pool.query("SELECT * FROM tasks WHERE id = $1", [id]);
    return result.rows[0] ? rowToTask(result.rows[0]) : null;
  }

  async list(): Promise<TaskRecord[]> {
    const result = await this.pool.query("SELECT * FROM tasks ORDER BY created_at DESC");
    return result.rows.map(rowToTask);
  }

  async update(
    id: string,
    patch: Partial<Pick<TaskRecord, "status" | "risk" | "phase" | "reviewPending" | "result">>,
  ): Promise<TaskRecord> {
    const current = await this.get(id);
    if (!current) {
      throw new Error(`task not found: ${id}`);
    }
    const next = { ...current, ...patch, updatedAt: now() };
    await this.pool.query(
      `UPDATE tasks SET status=$2, risk=$3, phase=$4, review_pending=$5, payload=$6, updated_at=$7 WHERE id=$1`,
      [id, next.status, next.risk, next.phase, next.reviewPending, { result: next.result }, next.updatedAt],
    );
    return next;
  }
}
