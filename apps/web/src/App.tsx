import { useEffect, useMemo, useState } from "react";
import type { TaskRecord } from "@durable-threads/contracts";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    throw new Error(`request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function upsertTask(tasks: TaskRecord[], task: TaskRecord): TaskRecord[] {
  const rest = tasks.filter((item) => item.id !== task.id);
  return [task, ...rest].sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
}

export function App() {
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [objective, setObjective] = useState("Fix a spelling typo in the README");
  const [allowedPaths, setAllowedPaths] = useState("README.md");
  const [acceptance, setAcceptance] = useState("The README is accurate.");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const selected = useMemo(
    () => tasks.find((task) => task.id === selectedId) ?? null,
    [tasks, selectedId],
  );

  async function refresh() {
    const payload = await api<{ tasks: TaskRecord[] }>("/v1/tasks");
    setTasks(payload.tasks);
  }

  useEffect(() => {
    void refresh().catch((cause: unknown) => setError(cause instanceof Error ? cause.message : String(cause)));
    const timer = setInterval(() => {
      void refresh().catch(() => undefined);
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    const source = new EventSource(`/v1/tasks/${selectedId}/stream`);
    source.onmessage = (event) => {
      const task = JSON.parse(event.data) as TaskRecord;
      setTasks((current) => upsertTask(current, task));
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, [selectedId]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const created = await api<{ id: string }>("/v1/tasks", {
      method: "POST",
      body: JSON.stringify({
        objective,
        allowedPaths: allowedPaths.split("\n").map((item) => item.trim()).filter(Boolean),
        acceptance: acceptance.split("\n").map((item) => item.trim()).filter(Boolean),
        waitForHumanReview: true,
      }),
    });
    setSelectedId(created.id);
    await refresh();
  }

  async function review(approved: boolean) {
    if (!selected) {
      return;
    }
    await api(`/v1/tasks/${selected.id}/review`, {
      method: "POST",
      body: JSON.stringify({ approved, note }),
    });
    await refresh();
  }

  return (
    <>
      <header>
        <h1>Durable Threads</h1>
        <p className="lede">
          Submit bounded work, watch policy and execution, and approve human gates. The hosted
          path uses TypeScript, Temporal when configured, and sandboxed headless executors.
        </p>
      </header>
      <div className="layout">
        <form onSubmit={(event) => void submit(event)}>
          <h2>New task</h2>
          <label htmlFor="objective">Objective</label>
          <textarea id="objective" rows={4} value={objective} onChange={(event) => setObjective(event.target.value)} />
          <label htmlFor="paths">Allowed paths</label>
          <textarea id="paths" rows={3} value={allowedPaths} onChange={(event) => setAllowedPaths(event.target.value)} />
          <label htmlFor="acceptance">Acceptance</label>
          <textarea
            id="acceptance"
            rows={3}
            value={acceptance}
            onChange={(event) => setAcceptance(event.target.value)}
          />
          <button type="submit">Submit task</button>
          {error ? <p>{error}</p> : null}
          <h2>Tasks</h2>
          <ul className="task-list">
            {tasks.map((task) => (
              <li key={task.id}>
                <button
                  type="button"
                  className={task.id === selectedId ? "active" : ""}
                  onClick={() => setSelectedId(task.id)}
                >
                  {task.objective}
                  <span className="status">{task.status}</span>
                </button>
              </li>
            ))}
          </ul>
        </form>
        <section className="panel">
          <h2>Status</h2>
          {selected ? (
            <>
              <p>
                Phase <strong>{selected.phase}</strong>
                {selected.risk ? ` · Risk ${selected.risk}` : ""}
              </p>
              {selected.reviewPending ? (
                <>
                  <label htmlFor="note">Review note</label>
                  <input id="note" value={note} onChange={(event) => setNote(event.target.value)} />
                  <button type="button" onClick={() => void review(true)}>
                    Approve
                  </button>
                  <button type="button" className="secondary" onClick={() => void review(false)}>
                    Reject
                  </button>
                </>
              ) : null}
              <pre>{JSON.stringify(selected.result ?? selected, null, 2)}</pre>
            </>
          ) : (
            <p>Select a task to inspect evidence and gates.</p>
          )}
        </section>
      </div>
    </>
  );
}
