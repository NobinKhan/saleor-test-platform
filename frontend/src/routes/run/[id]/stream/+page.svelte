<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { goto } from "$app/navigation";

  let runId = "";
  page.subscribe(p => { runId = p.params.id; });

  interface StatusCounts { pass: number; fail: number; warn: number; skip: number; }
  interface Event {
    type: string;
    current?: number;
    total?: number;
    current_endpoint?: string;
    status?: string;
    endpoint_kind?: string;
    category?: string;
    is_public?: boolean;
    response_time_ms?: number;
    error_message?: string;
    status_counts?: StatusCounts;
    passed?: number;
    failed?: number;
    warnings?: number;
    skipped?: number;
    version?: string;
  }

  let events: Event[] = [];
  let statusCounts: StatusCounts = { pass: 0, fail: 0, warn: 0, skip: 0 };
  let completed = false;
  let total = 0;
  let currentEndpoint = "";
  let error = "";
  let eventSource: EventSource | null = null;
  let version = "";

  onMount(async () => {
    if (!runId) return;
    const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
    ? 'http://72.60.199.155:5998'
    : 'http://localhost:5998';
  const url = `${API_BASE}/api/runs/${runId}/stream`;
    eventSource = new EventSource(url);

    eventSource.onmessage = (e) => {
      try {
        const data: Event = JSON.parse(e.data);
        events = [...events.slice(-99), data]; // Keep last 100

        if (data.type === "version") {
          version = data.version || "unknown";
        } else if (data.type === "result") {
          currentEndpoint = data.current_endpoint || "";
          total = data.total || 0;
          statusCounts = data.status_counts || statusCounts;
        } else if (data.type === "complete") {
          completed = true;
          statusCounts = {
            pass: data.passed || 0,
            fail: data.failed || 0,
            warn: data.warnings || 0,
            skip: data.skipped || 0,
          };
          total = data.total || 0;
          eventSource?.close();
        }
      } catch (err) {
        console.error("SSE parse error", err);
      }
    };

    eventSource.onerror = () => {
      error = "Connection lost. Test may still be running.";
      eventSource?.close();
    };
  });

  onDestroy(() => {
    eventSource?.close();
  });

  function goToReport() {
    goto(`/run/${runId}/report`);
  }
</script>

<svelte:head><title>Test Running — Saleor Test Platform</title></svelte:head>

<div class="stream-page">
  <div class="page-header">
    <div>
      <h1>Test in Progress</h1>
      <p class="subtitle">
        {#if version}Saleor {version} — {/if}
        {currentEndpoint || "Initializing..."}
      </p>
    </div>
    {#if completed}
      <a href="/run/{runId}/report" class="btn-primary">View Full Report →</a>
    {/if}
  </div>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  <div class="stats-row">
    <div class="stat-card">
      <span class="stat-value">{statusCounts.pass + statusCounts.fail + statusCounts.warn + statusCounts.skip}</span>
      <span class="stat-label">Tested</span>
    </div>
    <div class="stat-card pass">
      <span class="stat-value">{statusCounts.pass}</span>
      <span class="stat-label">Passed</span>
    </div>
    <div class="stat-card fail">
      <span class="stat-value">{statusCounts.fail}</span>
      <span class="stat-label">Failed</span>
    </div>
    <div class="stat-card warn">
      <span class="stat-value">{statusCounts.warn}</span>
      <span class="stat-label">Warnings</span>
    </div>
  </div>

  <div class="progress-section card">
    <div class="progress-header">
      <span>Progress</span>
      <span>{statusCounts.pass + statusCounts.fail + statusCounts.warn + statusCounts.skip} / {total}</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" style="width:{total ? ((statusCounts.pass+statusCounts.fail+statusCounts.warn+statusCounts.skip)/total*100).toFixed(1)+'%' : '0%'}"></div>
    </div>
  </div>

  <div class="recent-results card">
    <h3>Recent Results</h3>
    <div class="results-list">
      {#each events.slice(-20).reverse() as ev}
        {#if ev.type === "result" && ev.current_endpoint}
          <div class="result-item">
            <span class="badge badge-{ev.status}" style="min-width:60px;text-align:center;">{ev.status}</span>
            <span class="endpoint-name">{ev.current_endpoint}</span>
            <span class="endpoint-meta">{ev.endpoint_kind} · {ev.category}</span>
            <span class="response-time">{ev.response_time_ms || 0}ms</span>
          </div>
        {/if}
      {/each}
      {#if events.length === 0}
        <div class="empty">Waiting for results...</div>
      {/if}
    </div>
  </div>

  {#if completed}
    <div class="complete-banner">
      <h3>✓ Test Complete</h3>
      <p>
        {statusCounts.pass} passed, {statusCounts.fail} failed, {statusCounts.warn} warnings
        — {(statusCounts.pass / total * 100).toFixed(1)}% pass rate
      </p>
      <a href="/run/{runId}/report" class="btn-primary" style="margin-top:1rem;display:inline-block;">View Full Report</a>
    </div>
  {/if}
</div>

<style>
  .stream-page { max-width: 900px; }

  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
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

  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
  }

  .stat-value {
    display: block;
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .stat-card.pass .stat-value { color: var(--success); }
  .stat-card.fail .stat-value { color: var(--danger); }
  .stat-card.warn .stat-value { color: var(--warning); }

  .progress-section { margin-bottom: 1.5rem; }

  .progress-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
    color: var(--text-secondary);
  }

  .progress-track {
    height: 8px;
    background: var(--bg-primary);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--success), var(--accent));
    transition: width 0.3s ease;
  }

  .recent-results h3 { font-size: 1rem; margin-bottom: 1rem; }

  .results-list { display: flex; flex-direction: column; gap: 0.5rem; }

  .result-item {
    display: grid;
    grid-template-columns: 70px 1fr 150px 80px;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    background: var(--bg-primary);
    border-radius: 8px;
    font-size: 0.875rem;
  }

  .endpoint-name { font-family: monospace; color: var(--text-primary); }
  .endpoint-meta { color: var(--text-muted); font-size: 0.8rem; }
  .response-time { color: var(--text-secondary); text-align: right; font-size: 0.8rem; }

  .empty { color: var(--text-muted); padding: 1rem; text-align: center; }

  .complete-banner {
    margin-top: 1.5rem;
    background: var(--success-bg);
    border: 1px solid var(--success);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
  }

  .complete-banner h3 { color: var(--success); margin-bottom: 0.5rem; }
  .complete-banner p { color: var(--text-secondary); }
</style>
