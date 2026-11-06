export type Json = Record<string, any>; // Domain JSON is validated by versioned backend schemas.
let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export async function api<T = Json>(path: string, body?: unknown): Promise<T> {
  const res = await fetch("/api/v1" + path, {
    method: body === undefined ? "GET" : "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const data = await res.json();
  if (!res.ok)
    throw new Error(
      data.error ||
        (data.detail ? JSON.stringify(data.detail) : "Request failed"),
    );
  return data as T;
}
export const money = (n: number, currency = "INR") =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(n / 100);
export const short = (id: string = "") =>
  id.length > 18 ? id.slice(0, 8) + "…" + id.slice(-4) : id;
export const when = (date: string) => new Date(date).toLocaleString();
