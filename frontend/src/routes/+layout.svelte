<script lang="ts">
  import "../app.css";
  import { auth } from "$lib/api";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";

  let user: { email: string; name: string } | null = null;
  auth.subscribe(s => { user = s.user; });

  onMount(() => {
    const unsubscribe = page.subscribe(p => {
      if (!user && !p.url.pathname.startsWith("/login") && !p.url.pathname.startsWith("/register")) {
        goto("/login");
      }
    });
    return unsubscribe;
  });

  function logout() {
    auth.logout();
    goto("/login");
  }
</script>

<div class="app-shell">
  {#if user}
  <nav class="topnav">
    <div class="nav-brand">
      <a href="/dashboard">🔬 Saleor Test Platform</a>
    </div>
    <div class="nav-links">
      <a href="/dashboard" class:active={$page.url.pathname === "/dashboard"}>Dashboard</a>
    </div>
    <div class="nav-user">
      <span>{user.email}</span>
      <button class="btn-secondary btn-sm" on:click={logout}>Logout</button>
    </div>
  </nav>
  {/if}
  <main class="main-content">
    <slot />
  </main>
</div>

<style>
  .app-shell {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .topnav {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 0.75rem 1.5rem;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 50;
  }

  .nav-brand a {
    font-weight: 700;
    font-size: 1rem;
    color: var(--text-primary);
    text-decoration: none;
  }

  .nav-links {
    display: flex;
    gap: 1rem;
    flex: 1;
  }

  .nav-links a {
    color: var(--text-secondary);
    font-size: 0.9rem;
    padding: 0.25rem 0.5rem;
    border-radius: 6px;
    transition: color 0.15s, background 0.15s;
  }

  .nav-links a:hover, .nav-links a.active {
    color: var(--text-primary);
    background: var(--bg-card);
    text-decoration: none;
  }

  .nav-user {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }

  .main-content {
    flex: 1;
    padding: 2rem 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }
</style>
