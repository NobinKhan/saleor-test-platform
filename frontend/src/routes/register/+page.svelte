<script lang="ts">
  import { goto } from "$app/navigation";
  import { auth, api } from "$lib/api";

  let name = "";
  let email = "";
  let password = "";
  let confirmPassword = "";
  let error = "";
  let loading = false;

  async function handleRegister() {
    error = "";
    if (password !== confirmPassword) {
      error = "Passwords do not match";
      return;
    }
    if (password.length < 8) {
      error = "Password must be at least 8 characters";
      return;
    }
    loading = true;
    try {
      const data = await api.post("/api/auth/register", { email, name, password });
      auth.login({ id: "", email, name }, data.access_token, data.refresh_token);
      await goto("/dashboard");
    } catch (e: any) {
      error = e.message || "Registration failed";
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Register — Saleor Test Platform</title></svelte:head>

<div class="auth-page">
  <div class="auth-card card">
    <div class="auth-header">
      <h1>Create Account</h1>
      <p>Start testing Saleor APIs</p>
    </div>

    {#if error}
      <div class="error-banner">{error}</div>
    {/if}

    <form on:submit|preventDefault={handleRegister}>
      <div class="field">
        <label for="name">Full Name</label>
        <input id="name" type="text" bind:value={name} required placeholder="Nobin Khan" />
      </div>
      <div class="field">
        <label for="email">Email</label>
        <input id="email" type="email" bind:value={email} required placeholder="you@example.com" />
      </div>
      <div class="field">
        <label for="password">Password</label>
        <input id="password" type="password" bind:value={password} required placeholder="Min. 8 characters" />
      </div>
      <div class="field">
        <label for="confirm">Confirm Password</label>
        <input id="confirm" type="password" bind:value={confirmPassword} required placeholder="••••••••" />
      </div>
      <button class="btn-primary w-full" type="submit" disabled={loading}>
        {loading ? "Creating account..." : "Create Account"}
      </button>
    </form>

    <div class="auth-footer">
      Have an account? <a href="/login">Sign in</a>
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

  .auth-card { width: 100%; max-width: 400px; }

  .auth-header { margin-bottom: 1.5rem; text-align: center; }
  .auth-header h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.25rem; }
  .auth-header p { color: var(--text-secondary); font-size: 0.9rem; }

  .error-banner {
    background: var(--danger-bg);
    color: var(--danger);
    border: 1px solid var(--danger);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }

  form { display: flex; flex-direction: column; gap: 1rem; }
  .field { display: flex; flex-direction: column; gap: 0.375rem; }
  label { font-size: 0.875rem; font-weight: 500; color: var(--text-secondary); }
  .w-full { width: 100%; }
  .auth-footer { margin-top: 1.25rem; text-align: center; font-size: 0.875rem; color: var(--text-secondary); }
</style>
