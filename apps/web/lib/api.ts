export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(API_BASE + path, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(API_BASE + path, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
