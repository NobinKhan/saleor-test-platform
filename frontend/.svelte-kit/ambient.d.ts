
// this file is generated — do not edit it


/// <reference types="@sveltejs/kit" />

/**
 * This module provides access to environment variables that are injected _statically_ into your bundle at build time and are limited to _private_ access.
 * 
 * |         | Runtime                                                                    | Build time                                                               |
 * | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
 * | Private | [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private) | [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private) |
 * | Public  | [`$env/dynamic/public`](https://svelte.dev/docs/kit/$env-dynamic-public)   | [`$env/static/public`](https://svelte.dev/docs/kit/$env-static-public)   |
 * 
 * Static environment variables are [loaded by Vite](https://vitejs.dev/guide/env-and-mode.html#env-files) from `.env` files and `process.env` at build time and then statically injected into your bundle at build time, enabling optimisations like dead code elimination.
 * 
 * **_Private_ access:**
 * 
 * - This module cannot be imported into client-side code
 * - This module only includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured)
 * 
 * For example, given the following build time environment:
 * 
 * ```env
 * ENVIRONMENT=production
 * PUBLIC_BASE_URL=http://site.com
 * ```
 * 
 * With the default `publicPrefix` and `privatePrefix`:
 * 
 * ```ts
 * import { ENVIRONMENT, PUBLIC_BASE_URL } from '$env/static/private';
 * 
 * console.log(ENVIRONMENT); // => "production"
 * console.log(PUBLIC_BASE_URL); // => throws error during build
 * ```
 * 
 * The above values will be the same _even if_ different values for `ENVIRONMENT` or `PUBLIC_BASE_URL` are set at runtime, as they are statically replaced in your code with their build time values.
 */
declare module '$env/static/private' {
	export const GJS_DEBUG_TOPICS: string;
	export const VSCODE_CWD: string;
	export const npm_config_devdir: string;
	export const CURSOR_EXTENSION_HOST_ROLE: string;
	export const VSCODE_ESM_ENTRYPOINT: string;
	export const PUPPETEER_CACHE_DIR: string;
	export const USER: string;
	export const VSCODE_NLS_CONFIG: string;
	export const npm_config_user_agent: string;
	export const VSCODE_HANDLES_UNCAUGHT_ERRORS: string;
	export const CARGO_TARGET_DIR: string;
	export const CCACHE_DIR: string;
	export const BUN_INSTALL: string;
	export const XDG_SESSION_TYPE: string;
	export const PIP_CACHE_DIR: string;
	export const HOMEBREW_CACHE: string;
	export const NUGET_PACKAGES: string;
	export const npm_node_execpath: string;
	export const SHLVL: string;
	export const npm_config_noproxy: string;
	export const CHROME_DESKTOP: string;
	export const HOME: string;
	export const LESS: string;
	export const OLDPWD: string;
	export const DESKTOP_SESSION: string;
	export const npm_package_json: string;
	export const GIO_LAUNCHED_DESKTOP_FILE: string;
	export const LSCOLORS: string;
	export const VSCODE_IPC_HOOK: string;
	export const ZSH: string;
	export const GTK_MODULES: string;
	export const PAGER: string;
	export const CURSOR_WORKSPACE_LABEL: string;
	export const FNM_ARCH: string;
	export const MANAGERPID: string;
	export const npm_config_userconfig: string;
	export const npm_config_local_prefix: string;
	export const DBUS_SESSION_BUS_ADDRESS: string;
	export const SYSTEMD_EXEC_PID: string;
	export const CONDA_PKGS_DIRS: string;
	export const NO_COLOR: string;
	export const GIO_LAUNCHED_DESKTOP_FILE_PID: string;
	export const COLOR: string;
	export const VSCODE_CRASH_REPORTER_PROCESS_TYPE: string;
	export const COMPOSER_HOME: string;
	export const FNM_LOGLEVEL: string;
	export const FNM_VERSION_FILE_STRATEGY: string;
	export const WAYLAND_DISPLAY: string;
	export const LOGNAME: string;
	export const FORCE_COLOR: string;
	export const FNM_NODE_DIST_MIRROR: string;
	export const JOURNAL_STREAM: string;
	export const MANAGERPIDFDID: string;
	export const _: string;
	export const BUN_INSTALL_CACHE_DIR: string;
	export const npm_config_prefix: string;
	export const npm_config_npm_version: string;
	export const CURSOR_LAYOUT: string;
	export const MEMORY_PRESSURE_WATCH: string;
	export const XDG_SESSION_CLASS: string;
	export const GOMODCACHE: string;
	export const USERNAME: string;
	export const CP_HOME_DIR: string;
	export const TERM: string;
	export const FC_FONTATIONS: string;
	export const GNOME_DESKTOP_SESSION_ID: string;
	export const POETRY_CACHE_DIR: string;
	export const npm_config_node_gyp: string;
	export const PATH: string;
	export const INVOCATION_ID: string;
	export const YARN_CACHE_FOLDER: string;
	export const NODE: string;
	export const npm_package_name: string;
	export const GDK_BACKEND: string;
	export const GNOME_SETUP_DISPLAY: string;
	export const VSCODE_PROCESS_TITLE: string;
	export const XDG_MENU_PREFIX: string;
	export const XDG_RUNTIME_DIR: string;
	export const UV_CACHE_DIR: string;
	export const PLAYWRIGHT_BROWSERS_PATH: string;
	export const BUNDLE_PATH: string;
	export const DISPLAY: string;
	export const CURSOR_AGENT: string;
	export const LANG: string;
	export const XDG_CURRENT_DESKTOP: string;
	export const NX_CACHE_DIRECTORY: string;
	export const FNM_DIR: string;
	export const LS_COLORS: string;
	export const SBX_CHROME_API_RQ: string;
	export const XAUTHORITY: string;
	export const XDG_SESSION_DESKTOP: string;
	export const XMODIFIERS: string;
	export const CYPRESS_CACHE_FOLDER: string;
	export const npm_lifecycle_script: string;
	export const FNM_RESOLVE_ENGINES: string;
	export const SSH_AUTH_SOCK: string;
	export const PNPM_STORE_PATH: string;
	export const SHELL: string;
	export const GOCACHE: string;
	export const npm_package_version: string;
	export const npm_lifecycle_event: string;
	export const GDMSESSION: string;
	export const QT_ACCESSIBILITY: string;
	export const GJS_DEBUG_OUTPUT: string;
	export const GPG_AGENT_INFO: string;
	export const P9K_SSH: string;
	export const QT_IM_MODULE: string;
	export const npm_config_globalconfig: string;
	export const npm_config_init_module: string;
	export const FNM_MULTISHELL_PATH: string;
	export const PWD: string;
	export const NPM_CONFIG_CACHE: string;
	export const GRADLE_USER_HOME: string;
	export const npm_execpath: string;
	export const VSCODE_CODE_CACHE_PATH: string;
	export const XDG_DATA_DIRS: string;
	export const XDG_SESSION_EXTRA_DEVICE_ACCESS: string;
	export const npm_config_global_prefix: string;
	export const npm_command: string;
	export const FNM_COREPACK_ENABLED: string;
	export const TURBO_CACHE_DIR: string;
	export const MEMORY_PRESSURE_WRITE: string;
	export const QT_IM_MODULES: string;
	export const GEM_SPEC_CACHE: string;
	export const _ZO_DOCTOR: string;
	export const VSCODE_PID: string;
	export const INIT_CWD: string;
	export const EDITOR: string;
}

/**
 * This module provides access to environment variables that are injected _statically_ into your bundle at build time and are _publicly_ accessible.
 * 
 * |         | Runtime                                                                    | Build time                                                               |
 * | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
 * | Private | [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private) | [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private) |
 * | Public  | [`$env/dynamic/public`](https://svelte.dev/docs/kit/$env-dynamic-public)   | [`$env/static/public`](https://svelte.dev/docs/kit/$env-static-public)   |
 * 
 * Static environment variables are [loaded by Vite](https://vitejs.dev/guide/env-and-mode.html#env-files) from `.env` files and `process.env` at build time and then statically injected into your bundle at build time, enabling optimisations like dead code elimination.
 * 
 * **_Public_ access:**
 * 
 * - This module _can_ be imported into client-side code
 * - **Only** variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`) are included
 * 
 * For example, given the following build time environment:
 * 
 * ```env
 * ENVIRONMENT=production
 * PUBLIC_BASE_URL=http://site.com
 * ```
 * 
 * With the default `publicPrefix` and `privatePrefix`:
 * 
 * ```ts
 * import { ENVIRONMENT, PUBLIC_BASE_URL } from '$env/static/public';
 * 
 * console.log(ENVIRONMENT); // => throws error during build
 * console.log(PUBLIC_BASE_URL); // => "http://site.com"
 * ```
 * 
 * The above values will be the same _even if_ different values for `ENVIRONMENT` or `PUBLIC_BASE_URL` are set at runtime, as they are statically replaced in your code with their build time values.
 */
declare module '$env/static/public' {
	
}

/**
 * This module provides access to environment variables set _dynamically_ at runtime and that are limited to _private_ access.
 * 
 * |         | Runtime                                                                    | Build time                                                               |
 * | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
 * | Private | [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private) | [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private) |
 * | Public  | [`$env/dynamic/public`](https://svelte.dev/docs/kit/$env-dynamic-public)   | [`$env/static/public`](https://svelte.dev/docs/kit/$env-static-public)   |
 * 
 * Dynamic environment variables are defined by the platform you're running on. For example if you're using [`adapter-node`](https://github.com/sveltejs/kit/tree/main/packages/adapter-node) (or running [`vite preview`](https://svelte.dev/docs/kit/cli)), this is equivalent to `process.env`.
 * 
 * **_Private_ access:**
 * 
 * - This module cannot be imported into client-side code
 * - This module includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured)
 * 
 * > [!NOTE] In `dev`, `$env/dynamic` includes environment variables from `.env`. In `prod`, this behavior will depend on your adapter.
 * 
 * > [!NOTE] To get correct types, environment variables referenced in your code should be declared (for example in an `.env` file), even if they don't have a value until the app is deployed:
 * >
 * > ```env
 * > MY_FEATURE_FLAG=
 * > ```
 * >
 * > You can override `.env` values from the command line like so:
 * >
 * > ```sh
 * > MY_FEATURE_FLAG="enabled" npm run dev
 * > ```
 * 
 * For example, given the following runtime environment:
 * 
 * ```env
 * ENVIRONMENT=production
 * PUBLIC_BASE_URL=http://site.com
 * ```
 * 
 * With the default `publicPrefix` and `privatePrefix`:
 * 
 * ```ts
 * import { env } from '$env/dynamic/private';
 * 
 * console.log(env.ENVIRONMENT); // => "production"
 * console.log(env.PUBLIC_BASE_URL); // => undefined
 * ```
 */
declare module '$env/dynamic/private' {
	export const env: {
		GJS_DEBUG_TOPICS: string;
		VSCODE_CWD: string;
		npm_config_devdir: string;
		CURSOR_EXTENSION_HOST_ROLE: string;
		VSCODE_ESM_ENTRYPOINT: string;
		PUPPETEER_CACHE_DIR: string;
		USER: string;
		VSCODE_NLS_CONFIG: string;
		npm_config_user_agent: string;
		VSCODE_HANDLES_UNCAUGHT_ERRORS: string;
		CARGO_TARGET_DIR: string;
		CCACHE_DIR: string;
		BUN_INSTALL: string;
		XDG_SESSION_TYPE: string;
		PIP_CACHE_DIR: string;
		HOMEBREW_CACHE: string;
		NUGET_PACKAGES: string;
		npm_node_execpath: string;
		SHLVL: string;
		npm_config_noproxy: string;
		CHROME_DESKTOP: string;
		HOME: string;
		LESS: string;
		OLDPWD: string;
		DESKTOP_SESSION: string;
		npm_package_json: string;
		GIO_LAUNCHED_DESKTOP_FILE: string;
		LSCOLORS: string;
		VSCODE_IPC_HOOK: string;
		ZSH: string;
		GTK_MODULES: string;
		PAGER: string;
		CURSOR_WORKSPACE_LABEL: string;
		FNM_ARCH: string;
		MANAGERPID: string;
		npm_config_userconfig: string;
		npm_config_local_prefix: string;
		DBUS_SESSION_BUS_ADDRESS: string;
		SYSTEMD_EXEC_PID: string;
		CONDA_PKGS_DIRS: string;
		NO_COLOR: string;
		GIO_LAUNCHED_DESKTOP_FILE_PID: string;
		COLOR: string;
		VSCODE_CRASH_REPORTER_PROCESS_TYPE: string;
		COMPOSER_HOME: string;
		FNM_LOGLEVEL: string;
		FNM_VERSION_FILE_STRATEGY: string;
		WAYLAND_DISPLAY: string;
		LOGNAME: string;
		FORCE_COLOR: string;
		FNM_NODE_DIST_MIRROR: string;
		JOURNAL_STREAM: string;
		MANAGERPIDFDID: string;
		_: string;
		BUN_INSTALL_CACHE_DIR: string;
		npm_config_prefix: string;
		npm_config_npm_version: string;
		CURSOR_LAYOUT: string;
		MEMORY_PRESSURE_WATCH: string;
		XDG_SESSION_CLASS: string;
		GOMODCACHE: string;
		USERNAME: string;
		CP_HOME_DIR: string;
		TERM: string;
		FC_FONTATIONS: string;
		GNOME_DESKTOP_SESSION_ID: string;
		POETRY_CACHE_DIR: string;
		npm_config_node_gyp: string;
		PATH: string;
		INVOCATION_ID: string;
		YARN_CACHE_FOLDER: string;
		NODE: string;
		npm_package_name: string;
		GDK_BACKEND: string;
		GNOME_SETUP_DISPLAY: string;
		VSCODE_PROCESS_TITLE: string;
		XDG_MENU_PREFIX: string;
		XDG_RUNTIME_DIR: string;
		UV_CACHE_DIR: string;
		PLAYWRIGHT_BROWSERS_PATH: string;
		BUNDLE_PATH: string;
		DISPLAY: string;
		CURSOR_AGENT: string;
		LANG: string;
		XDG_CURRENT_DESKTOP: string;
		NX_CACHE_DIRECTORY: string;
		FNM_DIR: string;
		LS_COLORS: string;
		SBX_CHROME_API_RQ: string;
		XAUTHORITY: string;
		XDG_SESSION_DESKTOP: string;
		XMODIFIERS: string;
		CYPRESS_CACHE_FOLDER: string;
		npm_lifecycle_script: string;
		FNM_RESOLVE_ENGINES: string;
		SSH_AUTH_SOCK: string;
		PNPM_STORE_PATH: string;
		SHELL: string;
		GOCACHE: string;
		npm_package_version: string;
		npm_lifecycle_event: string;
		GDMSESSION: string;
		QT_ACCESSIBILITY: string;
		GJS_DEBUG_OUTPUT: string;
		GPG_AGENT_INFO: string;
		P9K_SSH: string;
		QT_IM_MODULE: string;
		npm_config_globalconfig: string;
		npm_config_init_module: string;
		FNM_MULTISHELL_PATH: string;
		PWD: string;
		NPM_CONFIG_CACHE: string;
		GRADLE_USER_HOME: string;
		npm_execpath: string;
		VSCODE_CODE_CACHE_PATH: string;
		XDG_DATA_DIRS: string;
		XDG_SESSION_EXTRA_DEVICE_ACCESS: string;
		npm_config_global_prefix: string;
		npm_command: string;
		FNM_COREPACK_ENABLED: string;
		TURBO_CACHE_DIR: string;
		MEMORY_PRESSURE_WRITE: string;
		QT_IM_MODULES: string;
		GEM_SPEC_CACHE: string;
		_ZO_DOCTOR: string;
		VSCODE_PID: string;
		INIT_CWD: string;
		EDITOR: string;
		[key: `PUBLIC_${string}`]: undefined;
		[key: `${string}`]: string | undefined;
	}
}

/**
 * This module provides access to environment variables set _dynamically_ at runtime and that are _publicly_ accessible.
 * 
 * |         | Runtime                                                                    | Build time                                                               |
 * | ------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
 * | Private | [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private) | [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private) |
 * | Public  | [`$env/dynamic/public`](https://svelte.dev/docs/kit/$env-dynamic-public)   | [`$env/static/public`](https://svelte.dev/docs/kit/$env-static-public)   |
 * 
 * Dynamic environment variables are defined by the platform you're running on. For example if you're using [`adapter-node`](https://github.com/sveltejs/kit/tree/main/packages/adapter-node) (or running [`vite preview`](https://svelte.dev/docs/kit/cli)), this is equivalent to `process.env`.
 * 
 * **_Public_ access:**
 * 
 * - This module _can_ be imported into client-side code
 * - **Only** variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`) are included
 * 
 * > [!NOTE] In `dev`, `$env/dynamic` includes environment variables from `.env`. In `prod`, this behavior will depend on your adapter.
 * 
 * > [!NOTE] To get correct types, environment variables referenced in your code should be declared (for example in an `.env` file), even if they don't have a value until the app is deployed:
 * >
 * > ```env
 * > MY_FEATURE_FLAG=
 * > ```
 * >
 * > You can override `.env` values from the command line like so:
 * >
 * > ```sh
 * > MY_FEATURE_FLAG="enabled" npm run dev
 * > ```
 * 
 * For example, given the following runtime environment:
 * 
 * ```env
 * ENVIRONMENT=production
 * PUBLIC_BASE_URL=http://example.com
 * ```
 * 
 * With the default `publicPrefix` and `privatePrefix`:
 * 
 * ```ts
 * import { env } from '$env/dynamic/public';
 * console.log(env.ENVIRONMENT); // => undefined, not public
 * console.log(env.PUBLIC_BASE_URL); // => "http://example.com"
 * ```
 * 
 * ```
 * 
 * ```
 */
declare module '$env/dynamic/public' {
	export const env: {
		[key: `PUBLIC_${string}`]: string | undefined;
	}
}
