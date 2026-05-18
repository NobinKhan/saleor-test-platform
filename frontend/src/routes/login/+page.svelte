<script lang="ts">
  import { goto } from "$app/navigation";
  import { auth, api } from "$lib/api";

  let email = "";
  let password = "";
  let error = "";
  let loading = false;

  async function handleLogin() {
    error = "";
    loading = true;
    try {
      const data = await api.post("/api/auth/login", { email, password });
      auth.login({ id: "", email, name: "" }, data.access_token, data.refresh_token);
      await goto("/dashboard");
    } catch (e: any) {
      error = e.message || "Login failed";
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Login — Saleor Test Platform</title></svelte:head>

<div class="auth-page">
  <div class="auth-card card">
    <div class="auth-header">
      <h1>Sign In</h1>
      <p>Access your test platform</p>
    </div>

    {#if error}
      <div class="error-banner">{error}</div>
    {/if}

    <form on:submit|preventDefault={handleLogin}>
      <div class="field">
        <label for="email">Email</label>
        <input id="email" type="email" bind:value={email} required placeholder="you@example.com" />
      </div>
      <div class="field">
        <label for="password">Password</label>
        <input id="password" type="password" bind:value={password} required placeholder="••••••••" />
      </div>
      <button class="btn-primary w-full" type="submit" disabled={loading}>
        {loading ? "Signing in..." : "Sign In"}
      </button>
    </form>

    <div class="auth-footer">
      No account? <a href="/register">Register here</a>
    </div>
  </div>
</div>

<style>
  .auth-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
  }

  .auth-card {
    width: 100%;
    max-width: 400px;
  }

  .auth-header {
    margin-bottom: 1.5rem;
    text-align: center;
  }

  .auth-header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }

  .auth-header p {
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  .error-banner {
    background: var(--danger-bg);
    color: var(--danger);
    border: 1px solid var(--danger);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
  }

  .w-full { width: 100%; }

  .auth-footer {
    margin-top: 1.25rem;
    text-align: center;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }
</style>
