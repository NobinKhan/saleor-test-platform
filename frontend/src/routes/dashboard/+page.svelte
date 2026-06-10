<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";

  interface TestRun {
    id: string;
    saleor_url: string;
    saleor_version: string | null;
    status: string;
    started_at: string;
    completed_at: string | null;
    total_tests: number;
    passed: number;
    failed: number;
    warnings: number;
    skipped: number;
    pass_rate: number;
  }

  let runs: TestRun[] = [];
  let loading = true;
  let error = "";
  let copiedId = "";

  onMount(async () => {
    try {
      runs = await api.get("/api/runs?limit=50");
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function statusBadge(s: string) {
    const map: Record<string, string> = {
      running: "badge-running", completed: "badge-pass", stopped: "badge-warn", failed: "badge-fail",
    };
    return map[s] || "badge-skip";
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString();
  }

  function shortId(id: string) {
    return id.slice(0, 8);
  }

  async function copyId(id: string) {
    try {
      await navigator.clipboard.writeText(id);
      copiedId = id;
      setTimeout(() => {
        if (copiedId === id) copiedId = "";
      }, 2000);
    } catch {
      window.prompt("Copy run ID:", id);
    }
  }
</script>

<svelte:head><title>Dashboard — Saleor Test Platform</title></svelte:head>

<div class="dashboard">
  <div class="page-header">
    <div>
      <h1>Dashboard</h1>
      <p class="subtitle">All test runs against Saleor servers</p>
    </div>
    <a href="/run/new" class="btn-primary">+ New Test Run</a>
  </div>

  {#if error}
    <div class="error-banner">{error}</div>
  {:else if loading}
    <div class="loading">Loading test runs...</div>
  {:else if runs.length === 0}
    <div class="empty-state card">
      <p>No test runs yet.</p>
      <a href="/run/new" class="btn-primary" style="display:inline-block;margin-top:0.75rem;">Create your first test run</a>
    </div>
  {:else}
    <div class="runs-table-wrap">
      <table class="runs-table">
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Server</th>
            <th>Saleor Version</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Pass Rate</th>
            <th>Started</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each runs as run}
            <tr>
              <td class="id-cell">
                <div class="id-cell-inner">
                  <code title={run.id}>{shortId(run.id)}</code>
                  <button type="button" class="btn-secondary btn-sm" on:click={() => copyId(run.id)}>Copy ID</button>
                  {#if copiedId === run.id}
                    <span class="copy-feedback">Copied!</span>
                  {/if}
                </div>
              </td>
              <td class="url-cell" title={run.saleor_url}>{run.saleor_url}</td>
              <td>{run.saleor_version || "—"}</td>
              <td><span class="badge {statusBadge(run.status)}">{run.status}</span></td>
              <td class="progress-cell">
                <div class="progress-bar-wrap">
                  {#if run.total_tests > 0}
                    <div class="progress-bar">
                      <div class="bar-pass" style="width:{(run.passed/run.total_tests*100).toFixed(1)}%"></div>
                      <div class="bar-fail" style="width:{(run.failed/run.total_tests*100).toFixed(1)}%"></div>
                      <div class="bar-warn" style="width:{(run.warnings/run.total_tests*100).toFixed(1)}%"></div>
                    </div>
                    <span class="progress-text">{run.passed}/{run.total_tests} passed</span>
                  {:else}
                    <span class="text-muted">—</span>
                  {/if}
                </div>
              </td>
              <td>
                {#if run.total_tests > 0}
                  <span class="pass-rate" class:high={run.pass_rate >= 80} class:mid={run.pass_rate >= 50 && run.pass_rate < 80} class:low={run.pass_rate < 50}>
                    {run.pass_rate}%
                  </span>
                {:else}—{/if}
              </td>
              <td class="text-secondary">{formatDate(run.started_at)}</td>
              <td>
                <div class="action-btns">
                  {#if run.status === "running"}
                    <a href="/run/{run.id}/stream" class="btn-secondary btn-sm">Live</a>
                  {:else}
                    <a href="/run/{run.id}/report" class="btn-secondary btn-sm">Report</a>
                    <a href="/run/new?compare={run.id}" class="btn-secondary btn-sm">Compare</a>
                  {/if}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .dashboard { max-width: 1400px; }

  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.75rem;
  }

  .page-header h1 { font-size: 1.5rem; font-weight: 700; }
  .subtitle { color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.25rem; }

  .error-banner {
    background: var(--danger-bg);
    color: var(--danger);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .loading { color: var(--text-secondary); padding: 2rem; text-align: center; }

  .empty-state { text-align: center; padding: 3rem; color: var(--text-secondary); }

  .runs-table-wrap { overflow-x: auto; }

  .runs-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .runs-table th {
    text-align: left;
    padding: 0.625rem 0.875rem;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    color: var(--text-secondary);
    font-weight: 600;
    white-space: nowrap;
  }

  .runs-table td {
    padding: 0.75rem 0.875rem;
    border-bottom: 1px solid var(--border-color);
    vertical-align: middle;
  }

  .runs-table tr:hover td { background: var(--bg-card); }

  .id-cell-inner {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex-wrap: wrap;
    white-space: nowrap;
  }

  .id-cell code { font-size: 0.8rem; }

  .copy-feedback {
    font-size: 0.75rem;
    color: var(--success);
    font-weight: 600;
  }

  .url-cell { max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: monospace; font-size: 0.8rem; }

  .progress-bar-wrap { display: flex; flex-direction: column; gap: 0.25rem; min-width: 120px; }

  .progress-bar {
    display: flex;
    height: 6px;
    background: var(--bg-primary);
    border-radius: 3px;
    overflow: hidden;
  }

  .bar-pass { background: var(--success); transition: width 0.3s; }
  .bar-fail { background: var(--danger); transition: width 0.3s; }
  .bar-warn { background: var(--warning); transition: width 0.3s; }

  .progress-text { font-size: 0.75rem; color: var(--text-secondary); }

  .pass-rate { font-weight: 700; }
  .pass-rate.high { color: var(--success); }
  .pass-rate.mid { color: var(--warning); }
  .pass-rate.low { color: var(--danger); }

  .text-secondary { color: var(--text-secondary); font-size: 0.8rem; }
  .text-muted { color: var(--text-muted); }

  .runs-table th:last-child,
  .runs-table td:last-child { white-space: nowrap; }

  .action-btns { display: flex; gap: 0.5rem; flex-wrap: wrap; }
</style>
