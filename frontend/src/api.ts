import { useQuery } from "@tanstack/react-query";

import type { AuditPayload } from "./types";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string; fields?: Record<string, string> };
      if (body.fields && Object.keys(body.fields).length > 0) {
        detail = Object.values(body.fields).join(" ");
      } else if (body.detail) {
        detail = body.detail;
      }
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(detail, response.status);
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("text/html")) {
    return (await response.text()) as T;
  }
  return (await response.json()) as T;
}

export function useAudit(auditId: string | undefined) {
  return useQuery({
    queryKey: ["audit", auditId],
    queryFn: () => api<AuditPayload>(`/api/audits/${auditId}`),
    enabled: Boolean(auditId),
  });
}
