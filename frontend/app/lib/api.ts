export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type WeekOption = {
  week_index: number;
  week_date: string;
};

export type WeeksResponse = {
  filename: string;
  weeks: WeekOption[];
};

export type PromptDetail = {
  id: number;
  filename: string;
  week_index: number;
  week_date: string;
  evidence_package: Record<string, unknown>;
  prompt_text: string;
  created_at: string;
};

export type PromptListItem = {
  id: number;
  filename: string;
  week_index: number;
  week_date: string;
  created_at: string;
};

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function fetchWeeks(file: File): Promise<WeeksResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/csv/weeks`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function generatePrompt(file: File, weekIndex: number): Promise<PromptDetail> {
  const form = new FormData();
  form.append("file", file);
  form.append("week_index", String(weekIndex));
  const res = await fetch(`${API_BASE}/prompts`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function listPrompts(): Promise<PromptListItem[]> {
  const res = await fetch(`${API_BASE}/prompts`, { cache: "no-store" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function getPrompt(id: number): Promise<PromptDetail> {
  const res = await fetch(`${API_BASE}/prompts/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
