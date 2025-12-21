const KEY = "ignored_expired_tasks";

function loadRaw(): number[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.filter((v) => Number.isInteger(v)).map((v) => Number(v));
    }
    return [];
  } catch {
    return [];
  }
}

function saveRaw(ids: number[]) {
  try {
    const unique = Array.from(new Set(ids));
    localStorage.setItem(KEY, JSON.stringify(unique));
  } catch {
    /* ignore storage errors */
  }
}

export function loadIgnoredExpiredTaskIds(): Set<number> {
  return new Set(loadRaw());
}

export function addIgnoredExpiredTaskId(taskId: number) {
  const ids = loadRaw();
  ids.push(taskId);
  saveRaw(ids);
}

export function isIgnoredExpiredTask(taskId: number): boolean {
  return loadIgnoredExpiredTaskIds().has(taskId);
}

export function clearIgnoredExpiredTasks() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
