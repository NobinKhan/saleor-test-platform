// Authentication store and API client
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

interface AuthUser {
  id: string;
  email: string;
  name: string;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
}

export function getApiBase(): string {
  return import.meta.env.PUBLIC_BACKEND_URL ?? 'http://localhost:5998';
}

function createAuthStore() {
  const stored = browser ? localStorage.getItem('auth') : null;
  const initial: AuthState = stored ? JSON.parse(stored) : { user: null, accessToken: null, refreshToken: null };
  const { subscribe, set, update } = writable<AuthState>(initial);

  return {
    subscribe,
    login(user: AuthUser, accessToken: string, refreshToken: string) {
      const state = { user, accessToken, refreshToken };
      if (browser) localStorage.setItem('auth', JSON.stringify(state));
      set(state);
    },
    logout() {
      if (browser) localStorage.removeItem('auth');
      set({ user: null, accessToken: null, refreshToken: null });
    },
    updateTokens(accessToken: string, refreshToken: string) {
      update(s => {
        const next = { ...s, accessToken, refreshToken };
        if (browser) localStorage.setItem('auth', JSON.stringify(next));
        return next;
      });
    },
    getAccessToken(): string | null {
      let token: string | null = null;
      subscribe(s => { token = s.accessToken; })();
      return token;
    },
  };
}

export const auth = createAuthStore();

export function apiHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = auth.getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

const API_BASE = getApiBase();

/** Paths where 401 means upstream/Saleor failure, not an expired harness JWT. */
const NO_REFRESH_ON_401 = ['/api/auth/saleor-token'];

function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' && item && 'msg' in item ? String((item as { msg: string }).msg) : String(item)))
      .join('; ');
  }
  return fallback;
}

async function apiFetch(path: string, options: RequestInit = {}, retried = false) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...apiHeaders(), ...(options.headers || {}) },
  });
  if (res.status === 401 && !NO_REFRESH_ON_401.some((p) => path.startsWith(p))) {
    if (!retried) {
      const refreshed = await refreshTokens();
      if (refreshed) {
        return apiFetch(path, options, true);
      }
    }
    auth.logout();
    if (typeof window !== 'undefined') window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(formatApiError(err.detail, res.statusText || 'API error'));
  }
  return res.json();
}

async function refreshTokens(): Promise<boolean> {
  let state: AuthState = { user: null, accessToken: null, refreshToken: null };
  auth.subscribe(s => { state = s; })();
  if (!state?.refreshToken) return false;
  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: state.refreshToken }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    auth.updateTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export const api = {
  get: (path: string) => apiFetch(path),
  post: (path: string, body?: unknown) => apiFetch(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  delete: (path: string) => apiFetch(path, { method: 'DELETE' }),
};

export function streamUrl(runId: string): string {
  const token = auth.getAccessToken();
  const base = `${getApiBase()}/api/runs/${runId}/stream`;
  if (!token) return base;
  return `${base}?access_token=${encodeURIComponent(token)}`;
}

export function exportUrl(runId: string, format: string): string {
  const token = auth.getAccessToken();
  const base = `${getApiBase()}/api/reports/${runId}/export/${format}`;
  if (!token) return base;
  return `${base}?access_token=${encodeURIComponent(token)}`;
}
