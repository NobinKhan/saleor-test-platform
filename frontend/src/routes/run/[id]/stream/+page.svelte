<script lang="ts">
  import { onDestroy } from "svelte";
  import { browser } from "$app/environment";
  import { page } from "$app/stores";
  import { auth, streamUrl } from "$lib/api";
  import { goto } from "$app/navigation";

  $: runId = $page.params.id ?? "";

  interface StatusCounts {
    pass: number;
    fail: number;
    warn: number;
    skip: number;
  }

  interface StreamEvent {
    type: string;
    message?: string;
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

  type ConnectionState = "connecting" | "live" | "complete" | "error";

  let events: StreamEvent[] = [];
  let activity: { time: string; text: string }[] = [];
  let statusCounts: StatusCounts = { pass: 0, fail: 0, warn: 0, skip: 0 };
  let completed = false;
  let total = 0;
  let currentEndpoint = "";
  let error = "";
  let eventSource: EventSource | null = null;
  let version = "";
  let phaseMessage = "Preparing test run…";
  let connectionState: ConnectionState = "connecting";
  let connectedRunId = "";

  function testedCount(): number {
    return statusCounts.pass + statusCounts.fail + statusCounts.warn + statusCounts.skip;
  }

  function progressPercent(): number {
    if (!total) return completed ? 100 : 0;
    return Math.min(100, (testedCount() / total) * 100);
  }

  function pushActivity(text: string) {
    const time = new Date().toLocaleTimeString();
    activity = [{ time, text }, ...activity].slice(0, 30);
  }

  function handleStreamEvent(data: StreamEvent) {
    events = [...events.slice(-99), data];

    switch (data.type) {
      case "connected":
        connectionState = "live";
        pushActivity("Connected to live stream");
        break;
      case "progress":
        phaseMessage = data.message || phaseMessage;
        if (data.total) total = data.total;
        pushActivity(data.message || "Working…");
        break;
      case "version":
        version = data.version || "unknown";
        phaseMessage = `Saleor ${version} detected`;
        pushActivity(phaseMessage);
        break;
      case "schema_diff":
        phaseMessage = "Schema compared — running tests";
        pushActivity("Schema introspection complete");
        break;
      case "result":
        connectionState = "live";
        currentEndpoint = data.current_endpoint || "";
        total = data.total || total;
        statusCounts = data.status_counts || statusCounts;
        phaseMessage = data.current_endpoint
          ? `Testing ${data.current_endpoint}`
          : "Running tests…";
        break;
      case "complete":
        completed = true;
        connectionState = "complete";
        statusCounts = {
          pass: data.passed ?? statusCounts.pass,
          fail: data.failed ?? statusCounts.fail,
          warn: data.warnings ?? statusCounts.warn,
          skip: data.skipped ?? statusCounts.skip,
        };
        total = data.total ?? total;
        phaseMessage = "Test run complete";
        pushActivity("All tests finished");
        closeStream();
        break;
    }
  }

  function closeStream() {
    eventSource?.close();
    eventSource = null;
  }

  function openStream(id: string) {
    closeStream();
    error = "";
    completed = false;
    connectionState = "connecting";
    phaseMessage = "Connecting to live stream…";
    events = [];
    activity = [];
    statusCounts = { pass: 0, fail: 0, warn: 0, skip: 0 };
    total = 0;
    version = "";
    currentEndpoint = "";

    const token = auth.getAccessToken();
    if (!token) {
      goto("/login");
      return;
    }

    eventSource = new EventSource(streamUrl(id));

    eventSource.onopen = () => {
      if (!completed) connectionState = "live";
    };

    eventSource.onmessage = (e) => {
      try {
        handleStreamEvent(JSON.parse(e.data) as StreamEvent);
      } catch (err) {
        console.error("SSE parse error", err);
      }
    };

    eventSource.onerror = () => {
      if (completed) return;
      if (eventSource?.readyState === EventSource.CONNECTING) {
        phaseMessage = "Reconnecting…";
        connectionState = "connecting";
        return;
      }
      if (eventSource?.readyState === EventSource.CLOSED) {
        error = "Connection lost. Refresh the page or open the report when the run finishes.";
        connectionState = "error";
        closeStream();
      }
    };
  }

  $: if (browser && runId && runId !== connectedRunId) {
    connectedRunId = runId;
    openStream(runId);
  }

  onDestroy(() => {
    closeStream();
  });
</script>

<svelte:head><title>Test Running — Saleor Test Platform</title></svelte:head>

<div class="stream-page">
  <div class="page-header">
    <div>
      <h1>Test in Progress</h1>
      <p class="subtitle">
        {#if version}<span class="version-tag">Saleor {version}</span>{/if}
        {phaseMessage}
      </p>
    </div>
    {#if completed}
      <a href="/run/{runId}/report" class="btn-primary">View Full Report →</a>
    {/if}
  </div>

  {#if connectionState === "connecting" && !error}
    <div class="status-banner connecting" role="status" aria-live="polite">
      <span class="spinner" aria-hidden="true"></span>
      <span>Connecting and waiting for the test worker…</span>
    </div>
  {/if}

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  <div class="stats-row">
    <div class="stat-card">
      <span class="stat-value">{testedCount()}</span>
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
      <span>
        {#if total}
          {testedCount()} / {total}
        {:else if !completed}
          Preparing…
        {:else}
          {testedCount()} / {total || testedCount()}
        {/if}
      </span>
    </div>
    <div class="progress-track" class:indeterminate={!total && !completed}>
      {#if total || completed}
        <div class="progress-fill" style="width:{progressPercent().toFixed(1)}%"></div>
      {:else}
        <div class="progress-fill indeterminate-bar"></div>
      {/if}
    </div>
    {#if currentEndpoint && !completed}
      <p class="current-endpoint">Current: <code>{currentEndpoint}</code></p>
    {/if}
  </div>

  <div class="panels">
    <div class="recent-results card">
      <h3>Recent Results</h3>
      <div class="results-list">
        {#each events.filter((ev) => ev.type === "result" && ev.current_endpoint).slice(-20).reverse() as ev}
          <div class="result-item">
            <span class="badge badge-{ev.status}" style="min-width:60px;text-align:center;">{ev.status}</span>
            <span class="endpoint-name">{ev.current_endpoint}</span>
            <span class="endpoint-meta">{ev.endpoint_kind} · {ev.category}</span>
            <span class="response-time">{ev.response_time_ms || 0}ms</span>
          </div>
        {:else}
          <div class="empty">
            {#if connectionState === "connecting"}
              <span class="spinner small" aria-hidden="true"></span>
              Waiting for first results…
            {:else}
              {phaseMessage}
            {/if}
          </div>
        {/each}
      </div>
    </div>

    <div class="activity-log card">
      <h3>Activity</h3>
      <ul>
        {#each activity as item}
          <li><time>{item.time}</time> {item.text}</li>
        {:else}
          <li class="muted">Events will appear here as the run progresses.</li>
        {/each}
      </ul>
    </div>
  </div>

  {#if completed}
    <div class="complete-banner">
      <h3>✓ Test Complete</h3>
      <p>
        {statusCounts.pass} passed, {statusCounts.fail} failed, {statusCounts.warn} warnings
        {#if total}
          — {(statusCounts.pass / total * 100).toFixed(1)}% pass rate
        {/if}
      </p>
      <a href="/run/{runId}/report" class="btn-primary" style="margin-top:1rem;display:inline-block;">View Full Report</a>
    </div>
  {/if}
</div>

<style>
  .stream-page { max-width: 960px; }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .page-header h1 { font-size: 1.5rem; font-weight: 700; }
  .subtitle {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-top: 0.35rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  .version-tag {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 0.1rem 0.45rem;
    font-size: 0.8rem;
    color: var(--accent);
  }

  .status-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    font-size: 0.9rem;
  }

  .status-banner.connecting {
    background: var(--bg-card);
    border: 1px solid var(--accent);
    color: var(--text-primary);
  }

  .error-banner {
    background: var(--danger-bg);
    color: var(--danger);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .spinner {
    width: 1.25rem;
    height: 1.25rem;
    border: 2px solid var(--border-color);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }

  .spinner.small {
    width: 1rem;
    height: 1rem;
    display: inline-block;
    vertical-align: middle;
    margin-right: 0.35rem;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  @media (max-width: 640px) {
    .stats-row { grid-template-columns: repeat(2, 1fr); }
    .panels { grid-template-columns: 1fr; }
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
    position: relative;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--success), var(--accent));
    transition: width 0.3s ease;
  }

  .progress-track.indeterminate .indeterminate-bar {
    width: 40% !important;
    animation: indeterminate 1.4s ease-in-out infinite;
  }

  @keyframes indeterminate {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(350%); }
  }

  .current-endpoint {
    margin-top: 0.5rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .current-endpoint code {
    font-family: monospace;
    color: var(--text-secondary);
  }

  .panels {
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 1rem;
  }

  .recent-results h3,
  .activity-log h3 {
    font-size: 1rem;
    margin-bottom: 1rem;
  }

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

  .empty {
    color: var(--text-muted);
    padding: 1.25rem;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
  }

  .activity-log ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-height: 320px;
    overflow-y: auto;
  }

  .activity-log li {
    font-size: 0.85rem;
    color: var(--text-secondary);
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--border-color);
  }

  .activity-log li:last-child { border-bottom: none; }

  .activity-log time {
    color: var(--text-muted);
    font-size: 0.75rem;
    margin-right: 0.5rem;
  }

  .activity-log .muted {
    color: var(--text-muted);
    font-style: italic;
    border: none;
  }

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
