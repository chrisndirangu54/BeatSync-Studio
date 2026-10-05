import { authToken } from "@/lib/firebase";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(API_BASE + path, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function authRequest(path: string, init: RequestInit = {}) {
  const token = await authToken();
  const headers = new Headers(init.headers || {});
  headers.set("Authorization", "Bearer " + token);
  const res = await fetch(API_BASE + path, { ...init, headers });
  if (!res.ok) throw new Error(await res.text());
  return res;
}

export async function authJSON<T>(path: string): Promise<T> {
  const res = await authRequest(path, { cache: "no-store" });
  return res.json();
}

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await authRequest(path, { method: "POST", body: form });
  return res.json();
}
