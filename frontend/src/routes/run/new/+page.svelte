<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";

  let saleor_url = "http://localhost:8000/graphql/";
  let saleor_email = "";
  let saleor_password = "";
  let test_scope = "catalog";
  let public_only = false;
  let concurrency = 5;
  let timeout_seconds = 30;
  const categories = [
    "products", "orders", "checkout", "payments", "shipping", "discounts",
    "channels", "categories", "collections", "attributes", "account",
    "giftcards", "pages", "warehouse", "meta", "shop", "plugins", "webhooks",
  ];
  let selectedCategories: string[] = [...categories];
  let loading = false;
  let startMessage = "";
  let error = "";

  function isValidSaleorEmail(email: string): boolean {
    const trimmed = email.trim();
    const parts = trimmed.split("@");
    return parts.length === 2 && parts[0].length > 0 && parts[1].length > 0;
  }

  async function startTest() {
    error = "";
    if (!saleor_url) {
      error = "Saleor server URL is required";
      return;
    }
    if (!saleor_email || !saleor_password) {
      error = "Saleor admin email and password are required";
      return;
    }
    if (!isValidSaleorEmail(saleor_email)) {
      error = "Enter a valid admin email (e.g. merchant@demo.basmalahub.local)";
      return;
    }
    try {
      new URL(saleor_url);
    } catch {
      error = "Invalid URL format";
      return;
    }

    loading = true;
    startMessage = "Authenticating and creating test run…";
    try {
      const run = await api.post("/api/runs", {
        saleor_url,
        saleor_email: saleor_email.trim(),
        saleor_password,
        test_scope,
        public_only,
        concurrency,
        timeout_seconds,
        categories: test_scope === "custom" ? selectedCategories : null,
      });
      startMessage = "Opening live progress…";
      await goto(`/run/${run.id}/stream`);
    } catch (e: any) {
      error = e.message || "Failed to start test run";
      loading = false;
      startMessage = "";
    }
  }
</script>

<svelte:head><title>New Test Run — Saleor Test Platform</title></svelte:head>

{#if loading}
  <div class="loading-overlay" role="status" aria-live="polite">
    <span class="spinner" aria-hidden="true"></span>
    <p>{startMessage || "Starting test run…"}</p>
  </div>
{/if}

<div class="new-run-page" class:dimmed={loading}>
  <div class="page-header">
    <h1>New Test Run</h1>
    <p class="subtitle">Configure and start a new Saleor API compatibility test</p>
  </div>

  <div class="form-card card">
    {#if error}
      <div class="error-banner">{error}</div>
    {/if}

    <form on:submit|preventDefault={startTest}>
      <div class="field">
        <label for="url">Saleor Server URL *</label>
        <input id="url" type="url" bind:value={saleor_url} required placeholder="https://your-store.saleor.cloud/graphql/" />
        <span class="hint">LAN URLs are used as-is. localhost is rewritten inside Docker to reach Saleor on the host.</span>
      </div>

      <div class="section-label">Saleor admin credentials *</div>
      <p class="section-hint">Dashboard staff login used for tokenCreate during the run. Internal domains (.local, .internal) are supported.</p>

      <div class="field-row">
        <div class="field">
          <label for="email">Admin Email</label>
          <input id="email" type="text" autocomplete="username" bind:value={saleor_email} required placeholder="merchant@demo.basmalahub.local" />
        </div>
        <div class="field">
          <label for="saleor_password">Admin Password</label>
          <input id="saleor_password" type="password" bind:value={saleor_password} required placeholder="••••••••" />
        </div>
      </div>

      <div class="field">
        <label for="scope">Test Scope</label>
        <select id="scope" bind:value={test_scope}>
          <option value="catalog">Catalog (recommended — static list only)</option>
          <option value="full">Full exhaustive (catalog + all introspected endpoints)</option>
          <option value="queries">Queries Only</option>
          <option value="mutations">Mutations Only</option>
          <option value="custom">Custom (by category)</option>
        </select>
      </div>

      {#if test_scope === "custom"}
        <div class="field">
          <span class="section-label">Categories</span>
          <div class="category-grid">
            {#each categories as cat}
              <label class="cat-check">
                <input type="checkbox" value={cat} checked={selectedCategories.includes(cat)}
                  on:change={(e) => {
                    if (e.currentTarget.checked) selectedCategories = [...selectedCategories, cat];
                    else selectedCategories = selectedCategories.filter(c => c !== cat);
                  }} />
                {cat}
              </label>
            {/each}
          </div>
        </div>
      {/if}

      <div class="field-row">
        <div class="field">
          <label for="concurrency">Concurrency</label>
          <input id="concurrency" type="number" min="1" max="20" bind:value={concurrency} />
        </div>
        <div class="field">
          <label for="timeout">Timeout (seconds)</label>
          <input id="timeout" type="number" min="5" max="120" bind:value={timeout_seconds} />
        </div>
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
  .loading-overlay {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(4px);
    color: var(--text-primary);
  }

  .loading-overlay p { font-size: 1rem; color: var(--text-secondary); }

  .loading-overlay .spinner {
    width: 2.5rem;
    height: 2.5rem;
    border: 3px solid var(--border-color);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .new-run-page.dimmed { pointer-events: none; opacity: 0.5; }
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

  .section-label { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; }
  .section-hint { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem; }
  form { display: flex; flex-direction: column; gap: 1rem; }
  .field { display: flex; flex-direction: column; gap: 0.375rem; }
  .field label { font-size: 0.875rem; font-weight: 500; color: var(--text-secondary); }
  .hint { font-size: 0.8rem; color: var(--text-muted); }
  .field-row { display: flex; gap: 0.75rem; align-items: flex-end; }
  .field-row .field { flex: 1; }
  .checkbox-field { flex-direction: row; align-items: center; gap: 0.5rem; }
  .checkbox-field input { width: auto; }
  .checkbox-field label { font-weight: 400; color: var(--text-primary); }
  .form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
  .category-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
  .cat-check { display: flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; cursor: pointer; }
</style>
