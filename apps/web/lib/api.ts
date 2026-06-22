import type {
  Job,
  JobListParams,
  JobListResponse,
  User,
  AuthResponse,
  RegisterBody,
  LoginBody,
  Application,
  CreateApplicationBody,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include", // send httpOnly cookie for auth
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, err.detail ?? "Request failed");
  }

  return res.json() as Promise<T>;
}

export const api = {
  jobs: {
    list: (params: JobListParams) => {
      // Build query params — skip undefined, convert booleans to strings
      const query = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null && v !== "") {
          query.set(k, String(v));
        }
      }
      return apiFetch<JobListResponse>(`/v1/jobs?${query.toString()}`);
    },
    get: (id: string) => apiFetch<Job>(`/v1/jobs/${id}`),
  },

  auth: {
    register: (body: RegisterBody) =>
      apiFetch<AuthResponse>("/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    login: (body: LoginBody) =>
      apiFetch<AuthResponse>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    logout: () => apiFetch("/v1/auth/logout", { method: "POST" }),
    me: () => apiFetch<User>("/v1/users/me"),
  },

  applications: {
    list: () => apiFetch<Application[]>("/v1/applications"),
    create: (body: CreateApplicationBody) =>
      apiFetch<Application>("/v1/applications", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    update: (id: string, body: Partial<Application>) =>
      apiFetch<Application>(`/v1/applications/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
  },
};
