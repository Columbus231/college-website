const defaultApiBase = import.meta.env.PROD ? "/api/v1" : "http://127.0.0.1:8000/api/v1";
const API_BASE = (import.meta.env.VITE_API_URL ?? defaultApiBase).replace(/\/$/, "");
const TOKEN_KEY = "college_access_token";

export type User = { id: number; email: string; full_name: string; roles: string[] };
export type Program = { id: number; name: string; level: string; description: string; published: boolean };
export type Application = { id: number; reference: string; program_id: number; status: string; statement: string; created_at: string };
export type UpdateItem = { id: number; title: string; body: string; category: string; date?: string; created_at?: string; published_at?: string | null; starts_at?: string; venue?: string };
export type FacultyMember = { id: number; name: string; designation: string; qualifications: string; research_interests: string };
export type AdminUser = { id: number; email: string; full_name: string; roles: string[]; is_active: boolean };
export type AdminFaculty = { id: number; user_id: number; name: string; designation: string; qualifications: string; approved: boolean };

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("The college service could not be reached. Check the connection and try again.");
    }
    throw error;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  contact: (body: { name: string; email: string; interest: string; message: string }) =>
    request<{ message: string }>("/contact", { method: "POST", body: JSON.stringify(body) }),
  programs: () => request<Program[]>("/programs"),
  news: () => request<UpdateItem[]>("/news"),
  notices: () => request<UpdateItem[]>("/notices"),
  events: () => request<UpdateItem[]>("/events"),
  faculty: () => request<FacultyMember[]>("/faculty"),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (full_name: string, email: string, password: string) =>
    request<{ message: string }>("/auth/register", { method: "POST", body: JSON.stringify({ full_name, email, password }) }),
  resendVerification: (email: string) =>
    request<{ message: string }>("/auth/resend-verification", { method: "POST", body: JSON.stringify({ email }) }),
  verifyEmail: (token: string) =>
    request<{ message: string }>("/auth/verify-email", { method: "POST", body: JSON.stringify({ token }) }),
  requestPasswordReset: (email: string) =>
    request<{ message: string }>("/auth/password-reset/request", { method: "POST", body: JSON.stringify({ email }) }),
  resetPassword: (token: string, password: string) =>
    request<{ message: string }>("/auth/password-reset/confirm", { method: "POST", body: JSON.stringify({ token, password }) }),
  me: () => request<User>("/auth/me"),
  applications: () => request<Application[]>("/applications/mine"),
  createApplication: (program_id: number, statement = "") =>
    request<Application>("/applications", { method: "POST", body: JSON.stringify({ program_id, statement }) }),
  submitApplication: (id: number) =>
    request<Application>(`/applications/${id}/submit`, { method: "POST" }),
  uploadApplicationDocument: (id: number, file: File) => {
    const body = new FormData();
    body.set("file", file);
    return request<{ message: string }>(`/applications/${id}/documents`, { method: "POST", body });
  },
  adminApplications: () => request<Application[]>("/admin/applications"),
  adminUsers: () => request<AdminUser[]>("/admin/users"),
  assignUserRole: (id: number, role: string, student_number = "") =>
    request<AdminUser>(`/admin/users/${id}/role`, { method: "PATCH", body: JSON.stringify({ role, student_number }) }),
  adminFaculty: () => request<AdminFaculty[]>("/admin/faculty"),
  approveFaculty: (id: number) => request<{ id: number; approved: boolean }>(`/admin/faculty/${id}/approve`, { method: "PATCH" }),
  createProgram: (body: Omit<Program, "id"> & { level: string; eligibility?: string; duration?: string }) =>
    request<Program>("/admin/programs", { method: "POST", body: JSON.stringify(body) }),
  createNews: (body: { title: string; slug: string; body: string; category: string; published: boolean }) =>
    request<UpdateItem>("/admin/news", { method: "POST", body: JSON.stringify(body) }),
  createNotice: (body: { title: string; body: string; category: string; published: boolean }) =>
    request<UpdateItem>("/admin/notices", { method: "POST", body: JSON.stringify(body) }),
  createEvent: (body: { title: string; description: string; venue: string; starts_at: string; published: boolean }) =>
    request<UpdateItem>("/admin/events", { method: "POST", body: JSON.stringify(body) }),
  setApplicationStatus: (id: number, status: string) =>
    request<Application>(`/admin/applications/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
};
