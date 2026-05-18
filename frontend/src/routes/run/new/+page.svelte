<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";

  let saleor_url = "http://localhost:8000/graphql/";
  let saleor_email = "";
  let saleor_password = "";
  let saleor_token = ""; // manual token override
  let test_scope = "full";
  let public_only = false;
  let loading = false;
  let error = "";
  let testing_auth = false;

  async function testAuth() {
    if (!saleor_email || !saleor_password || !saleor_url) {
      error = "Fill Saleor URL, email and password first";
      return;
    }
    testing_auth = true;
    error = "";
    try {
      const resp = await api.post("/api/auth/saleor-token", {
        saleor_url,
        email: saleor_email,
        password: saleor_password,
      });
      saleor_token = resp.token;
    } catch (e: any) {
      error = e.message || "Authentication failed";
    } finally {
      testing_auth = false;
    }
  }

  async function startTest() {
    error = "";
    if (!saleor_url) {
      error = "Saleor server URL is required";
      return;
    }
    try {
      new URL(saleor_url);
    } catch {
      error = "Invalid URL format";
      return;
    }

    loading = true;
    try {
      const run = await api.post("/api/runs", {
        saleor_url,
        saleor_email: saleor_email || null,
        saleor_password: saleor_password || null,
        saleor_token: saleor_token || null,
        test_scope,
        public_only,
      });
      await goto(`/run/${run.id}/stream`);
    } catch (e: any) {
      error = e.message || "Failed to start test run";
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>New Test Run — Saleor Test Platform</title></svelte:head>

<div class="new-run-page">
  <div class="page-header">
    <h1>New Test Run</h1>
    <p class="subtitle">Configure and start a new Saleor API test</p>
  </div>

  <div class="form-card card">
    {#if error}
      <div class="error-banner">{error}</div>
    {/if}

    <form on:submit|preventDefault={startTest}>
      <div class="field">
        <label for="url">Saleor Server URL *</label>
        <input id="url" type="url" bind:value={saleor_url} required placeholder="https://your-store.saleor.cloud/graphql/" />
        <span class="hint">The GraphQL endpoint of your Saleor instance</span>
      </div>

      <div class="section-label">Saleor Authentication</div>
      <p class="section-hint">Provide admin credentials so the test system can authenticate automatically. Leave token empty to use credentials instead.</p>

      <div class="field-row">
        <div class="field">
          <label for="email">Admin Email</label>
          <input id="email" type="email" bind:value={saleor_email} placeholder="admin@example.com" />
        </div>
        <div class="field">
          <label for="saleor_password">Admin Password</label>
          <input id="saleor_password" type="password" bind:value={saleor_password} placeholder="••••••••" />
        </div>
        <button type="button" class="btn-secondary test-btn" on:click={testAuth} disabled={testing_auth || !saleor_email || !saleor_password}>
          {testing_auth ? "Testing..." : "Test Auth"}
        </button>
      </div>

      {#if saleor_token}
        <div class="auth-ok">✓ Authenticated — token ready</div>
      {/if}

      <div class="divider"></div>

      <div class="field">
        <label for="token">API Token (Optional)</label>
        <input id="token" type="password" bind:value={saleor_token} placeholder="Bearer token — leave empty to use email/password above" />
        <span class="hint">Manual override — takes precedence over credentials above</span>
      </div>

      <div class="divider"></div>

      <div class="field">
        <label for="scope">Test Scope</label>
        <select id="scope" bind:value={test_scope}>
          <option value="full">Full (Queries + Mutations)</option>
          <option value="queries">Queries Only</option>
          <option value="mutations">Mutations Only</option>
        </select>
      </div>

      <div class="field checkbox-field">
        <input id="public" type="checkbox" bind:checked={public_only} />
        <label for="public">Test public endpoints only (skip authenticated)</label>
      </div>

      <div class="form-actions">
        <a href="/dashboard" class="btn-secondary">Cancel</a>
        <button class="btn-primary" type="submit" disabled={loading}>
          {loading ? "Starting..." : "Start Test Run"}
        </button>
      </div>
    </form>
  </div>
</div>

<style>
  .new-run-page { max-width: 700px; }

  .page-header { margin-bottom: 1.5rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; }
  .subtitle { color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.25rem; }

  .form-card { padding: 1.5rem; }

  .error-banner {
    background: var(--danger-bg);
    color: var(--danger);
    border: 1px solid var(--danger);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }

  .section-label {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
  }

  .section-hint {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
  }

  form { display: flex; flex-direction: column; gap: 1rem; }

  .field { display: flex; flex-direction: column; gap: 0.375rem; }
  .field label { font-size: 0.875rem; font-weight: 500; color: var(--text-secondary); }
  .hint { font-size: 0.8rem; color: var(--text-muted); }

  .field-row {
    display: flex;
    gap: 0.75rem;
    align-items: flex-end;
  }
  .field-row .field { flex: 1; }
  .test-btn { flex-shrink: 0; white-space: nowrap; height: 40px; }

  .auth-ok {
    background: var(--success-bg);
    color: var(--success);
    border: 1px solid var(--success);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
  }

  .divider {
    height: 1px;
    background: var(--border-color);
    margin: 0.25rem 0;
  }

  .checkbox-field { flex-direction: row; align-items: center; gap: 0.5rem; }
  .checkbox-field input { width: auto; }
  .checkbox-field label { font-weight: 400; color: var(--text-primary); }

  .form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
</style>