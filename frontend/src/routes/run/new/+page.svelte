<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api } from "$lib/api";

  interface PriorRun {
    id: string;
    saleor_url: string;
    saleor_version: string | null;
    status: string;
    started_at: string;
    pass_rate: number;
  }

  let saleor_url = "http://localhost:8000/graphql/";
  let saleor_email = "";
  let saleor_password = "";
  let showPassword = false;
  let concurrency = 1;
  let timeout_seconds = 30;
  let compare_run_id = "";
  let priorRuns: PriorRun[] = [];
  let cloneFromRunId: string | null = null;

  let prefillMessage = "";
  let loading = false;
  let prefillLoading = false;
  let startMessage = "";
  let error = "";
  let resolvedSaleorUrl: string | null = null;
  let preflightSeedInfo: {
    seeded_keys: string[];
    storefront_session_ready: boolean;
  } | null = null;

  function shortId(id: string): string {
    return id.slice(0, 8);
  }

  function isValidSaleorEmail(email: string): boolean {
    const trimmed = email.trim();
    const parts = trimmed.split("@");
    return parts.length === 2 && parts[0].length > 0 && parts[1].length > 0;
  }

  onMount(async () => {
    const from = $page.url.searchParams.get("from");
    const compare = $page.url.searchParams.get("compare");
    if (compare) compare_run_id = compare;

    try {
      priorRuns = await api.get("/api/runs?limit=50");
      priorRuns = priorRuns.filter((r) => r.status === "completed");
    } catch {
      priorRuns = [];
    }

    if (!from) return;

    cloneFromRunId = from;
    prefillLoading = true;
    try {
      const run = await api.get(`/api/runs/${from}`);
      saleor_url = run.saleor_url;
      saleor_email = run.saleor_email ?? "";
      concurrency = run.concurrency ?? 1;
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
    startMessage = "Pre-flight validation…";
    try {
      const payload: Record<string, unknown> = {
        saleor_url,
        saleor_email: saleor_email.trim(),
        concurrency,
        timeout_seconds,
      };
      if (compare_run_id.trim()) {
        payload.compare_run_id = compare_run_id.trim();
      }
      const trimmedPassword = saleor_password.trim();
      if (trimmedPassword) {
        payload.saleor_password = trimmedPassword;
      }
      if (cloneFromRunId) {
        payload.clone_from_run_id = cloneFromRunId;
      }

      const validation = await api.post("/api/runs/validate", payload);
      const requestedUrl = (validation.requested_saleor_url as string | undefined) ?? saleor_url;
      const resolvedUrl = validation.resolved_saleor_url as string | undefined;
      resolvedSaleorUrl =
        resolvedUrl && resolvedUrl !== requestedUrl ? resolvedUrl : null;

      const blockingIssues: string[] = validation.blocking_issues ?? [];
      const warningIssues: string[] = validation.warning_issues ?? [];
      preflightSeedInfo = {
        seeded_keys: (validation.seeded_keys as string[] | undefined) ?? [],
        storefront_session_ready: Boolean(validation.storefront_session_ready),
      };
      if (blockingIssues.length > 0) {
        const confirmMsg = blockingIssues.length === 1
          ? `Pre-flight issue:\n  ${blockingIssues[0]}\n\nStart anyway?`
          : `Pre-flight issues:\n  ${blockingIssues.map((i: string) => `  • ${i}`).join("\n")}\n\nStart anyway?`;
        if (!confirm(confirmMsg)) {
          loading = false;
          startMessage = "";
          return;
        }
      } else if (warningIssues.length > 0) {
        console.warn("Pre-flight warnings (non-blocking):", warningIssues);
      }

      startMessage = "Creating test run…";
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
    <p class="subtitle">Full-system compatibility — L1 probes, L3 Dashboard + Storefront, scenarios, and variants</p>
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
        {#if resolvedSaleorUrl}
          <span class="hint resolved-url">Harness will connect to {resolvedSaleorUrl}</span>
        {/if}
      </div>

      <div class="section-label">Saleor admin credentials *</div>
      <p class="section-hint">Dashboard staff login used for tokenCreate during the run. Customer account is auto-provisioned.</p>

      <div class="field-row">
        <div class="field">
          <label for="email">Admin Email</label>
          <input id="email" type="text" autocomplete="username" bind:value={saleor_email} required placeholder="merchant@demo.basmalahub.local" />
        </div>
        <div class="field password-field">
          <label for="saleor_password">Admin Password</label>
          <div class="password-wrap">
            {#if showPassword}
              <input
                id="saleor_password"
                type="text"
                bind:value={saleor_password}
                placeholder={cloneFromRunId ? "Leave blank to reuse stored password" : "••••••••"}
                required={!cloneFromRunId}
              />
            {:else}
              <input
                id="saleor_password"
                type="password"
                bind:value={saleor_password}
                placeholder={cloneFromRunId ? "Leave blank to reuse stored password" : "••••••••"}
                required={!cloneFromRunId}
              />
            {/if}
            <button
              type="button"
              class="btn-secondary btn-sm toggle-pw"
              on:click={() => (showPassword = !showPassword)}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>
      </div>

      <div class="field">
        <label for="compare_run_id">Compare with prior run (optional)</label>
        {#if priorRuns.length > 0}
          <select id="compare_run_id" bind:value={compare_run_id}>
            <option value="">— None —</option>
            {#each priorRuns as run}
              <option value={run.id}>
                {shortId(run.id)} · {new Date(run.started_at).toLocaleString()} · {run.pass_rate}% · {run.saleor_url}
              </option>
            {/each}
          </select>
        {:else}
          <input id="compare_run_id" type="text" bind:value={compare_run_id} placeholder="Run UUID for side-by-side report" />
        {/if}
      </div>

      <div class="field-row">
        <div class="field">
          <label for="concurrency">Concurrency</label>
          <input id="concurrency" type="number" min="1" max="20" bind:value={concurrency} />
          <p class="field-hint">Certification uses mutation-first harness seeding on the target (no demo data required).</p>
        </div>
        <div class="field">
          <label for="timeout">Timeout (seconds)</label>
          <input id="timeout" type="number" min="5" max="120" bind:value={timeout_seconds} />
        </div>
      </div>

      {#if preflightSeedInfo}
        <div class="preflight-chips" role="status">
          {#if preflightSeedInfo.storefront_session_ready}
            <span class="chip chip-ok">Storefront session ready</span>
          {/if}
          {#each preflightSeedInfo.seeded_keys.slice(0, 8) as key}
            <span class="chip">{key}</span>
          {/each}
          {#if preflightSeedInfo.seeded_keys.length > 8}
            <span class="chip">+{preflightSeedInfo.seeded_keys.length - 8} more</span>
          {/if}
        </div>
      {/if}

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
  .hint.resolved-url { display: block; margin-top: 0.25rem; color: var(--accent, #6366f1); }
  .field-row { display: flex; gap: 0.75rem; align-items: flex-end; }
  .field-row .field { flex: 1; }
  .password-wrap { display: flex; gap: 0.5rem; align-items: stretch; }
  .password-wrap input { flex: 1; }
  .toggle-pw { flex-shrink: 0; align-self: stretch; }
  .form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
  .preflight-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: -0.25rem; }
  .chip {
    font-size: 0.75rem;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    background: var(--surface-elevated, rgba(255, 255, 255, 0.06));
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
  }
  .chip-ok { border-color: var(--success, #22c55e); color: var(--success, #22c55e); }
</style>
