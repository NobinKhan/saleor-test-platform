// Authentication store
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
  };
}

export const auth = createAuthStore();

export function apiHeaders(): Record<string, string> {
  let headers: Record<string, string> = { 'Content-Type': 'application/json' };
  let token: string | null = null;
  auth.subscribe(s => { token = s.accessToken; })();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// API base URL - use public IP when running in browser
const API_BASE = typeof window !== 'undefined' ? 'http://72.60.199.155:5998' : 'http://localhost:5998';

async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...apiHeaders(), ...(options.headers || {}) },
  });
  if (res.status === 401) {
    // Try refresh
    const refreshed = await refreshTokens();
    if (refreshed) {
      return apiFetch(path, options);
    } else {
      auth.logout();
      if (typeof window !== 'undefined') window.location.href = '/login';
      throw new Error('Unauthorized');
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API error');
  }
  return res.json();
}

async function refreshTokens(): Promise<boolean> {
  let state: AuthState;
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
