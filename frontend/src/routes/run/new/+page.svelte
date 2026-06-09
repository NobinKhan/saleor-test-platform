<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api } from "$lib/api";

  let saleor_url = "http://localhost:8000/graphql/";
  let saleor_email = "";
  let saleor_password = "";
  let concurrency = 5;
  let timeout_seconds = 30;
  let test_scope = "full+client+storefront";
  let categories = "";
  let compare_run_id = "";
  let saleor_customer_email = "";
  let saleor_customer_password = "";
  let cloneFromRunId: string | null = null;

  const scopeOptions = [
    { value: "full+client+storefront", label: "Full + Dashboard + Storefront (certification)" },
    { value: "full+client", label: "Full + Dashboard L3" },
    { value: "client-storefront", label: "Storefront L3 only" },
    { value: "client-dashboard", label: "Dashboard L3 only" },
    { value: "full", label: "L1 probes only" },
    { value: "scenarios", label: "L4 scenarios" },
    { value: "variants", label: "Input variants" },
    { value: "custom", label: "Custom categories" },
  ];
  let prefillMessage = "";
  let loading = false;
  let prefillLoading = false;
  let startMessage = "";
  let error = "";

  function isValidSaleorEmail(email: string): boolean {
    const trimmed = email.trim();
    const parts = trimmed.split("@");
    return parts.length === 2 && parts[0].length > 0 && parts[1].length > 0;
  }

  onMount(async () => {
    const from = $page.url.searchParams.get("from");
    if (!from) return;

    cloneFromRunId = from;
    prefillLoading = true;
    try {
      const run = await api.get(`/api/runs/${from}`);
      saleor_url = run.saleor_url;
      saleor_email = run.saleor_email ?? "";
      concurrency = run.concurrency ?? 5;
      timeout_seconds = run.timeout_seconds ?? 30;
      prefillMessage =
        "Prefilled from previous run — review settings and click Start when ready.";
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : "Could not load previous run settings";
      cloneFromRunId = null;
    } finally {
      prefillLoading = false;
    }
  });

  async function startTest() {
    error = "";
    if (!saleor_url) {
      error = "Saleor server URL is required";
      return;
    }
    if (!saleor_email) {
      error = "Saleor admin email is required";
      return;
    }
    if (!saleor_password && !cloneFromRunId) {
      error = "Saleor admin password is required";
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
      const payload: Record<string, unknown> = {
        saleor_url,
        saleor_email: saleor_email.trim(),
        test_scope,
        public_only: false,
        concurrency,
        timeout_seconds,
      };
      if (test_scope === "custom" && categories.trim()) {
        payload.categories = categories.split(",").map((c) => c.trim()).filter(Boolean);
      }
      if (compare_run_id.trim()) {
        payload.compare_run_id = compare_run_id.trim();
      }
      if (saleor_customer_email.trim()) {
        payload.saleor_customer_email = saleor_customer_email.trim();
      }
      if (saleor_customer_password) {
        payload.saleor_customer_password = saleor_customer_password;
      }
      if (saleor_password) {
        payload.saleor_password = saleor_password;
      }
      if (cloneFromRunId) {
        payload.clone_from_run_id = cloneFromRunId;
      }
      const run = await api.post("/api/runs", payload);
      startMessage = "Opening live progress…";
      await goto(`/run/${run.id}/stream`);
    } catch (e: unknown) {
      error = e instanceof Error ? e.message : "Failed to start test run";
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
    <p class="subtitle">Saleor compatibility certification — L1 probes, L3 Dashboard + Storefront bundles, scenarios, variants</p>
  </div>

  <div class="form-card card">
    {#if prefillLoading}
      <div class="info-banner">Loading previous run settings…</div>
    {/if}
    {#if prefillMessage}
      <div class="info-banner">{prefillMessage}</div>
    {/if}
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
          <input
            id="saleor_password"
            type="password"
            bind:value={saleor_password}
            placeholder={cloneFromRunId ? "Leave blank to reuse stored password" : "••••••••"}
            required={!cloneFromRunId}
          />
        </div>
      </div>

      <div class="field">
        <label for="test_scope">Test scope</label>
        <select id="test_scope" bind:value={test_scope}>
          {#each scopeOptions as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      </div>

      {#if test_scope === "custom"}
        <div class="field">
          <label for="categories">Categories (comma-separated)</label>
          <input id="categories" type="text" bind:value={categories} placeholder="products, orders, checkout" />
        </div>
      {/if}

      <div class="field">
        <label for="compare_run_id">Compare with prior run (optional UUID)</label>
        <input id="compare_run_id" type="text" bind:value={compare_run_id} placeholder="Previous run ID for side-by-side report" />
      </div>

      <div class="section-label">Storefront customer credentials (optional)</div>
      <p class="section-hint">Used for storefront L3 bundles tagged with customer auth. Defaults to harness seed customer if omitted.</p>
      <div class="field-row">
        <div class="field">
          <label for="customer_email">Customer Email</label>
          <input id="customer_email" type="text" bind:value={saleor_customer_email} placeholder="customer@example.com" />
        </div>
        <div class="field">
          <label for="customer_password">Customer Password</label>
          <input id="customer_password" type="password" bind:value={saleor_customer_password} />
        </div>
      </div>

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

      <div class="form-actions">
        <a href="/dashboard" class="btn-secondary">Cancel</a>
        <button class="btn-primary" type="submit" disabled={loading || prefillLoading}>
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

  .info-banner {
    background: var(--surface-elevated, rgba(255, 255, 255, 0.05));
    color: var(--text-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
    margin-bottom: 1rem;
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

  .section-label { font-size: 0.9rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem; }
  .section-hint { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem; }
  form { display: flex; flex-direction: column; gap: 1rem; }
  .field { display: flex; flex-direction: column; gap: 0.375rem; }
  .field label { font-size: 0.875rem; font-weight: 500; color: var(--text-secondary); }
  .hint { font-size: 0.8rem; color: var(--text-muted); }
  .field-row { display: flex; gap: 0.75rem; align-items: flex-end; }
  .field-row .field { flex: 1; }
  .form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
</style>
