<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  onMount(() => {
    goto('/dashboard');
  });
</script>

<div class="redirect-msg">
  <p>Redirecting to dashboard...</p>
</div>

<style>
  .redirect-msg {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }
</style>