# RAM-safe defaults for Docker builds, compose, and Node tooling.
# Source from stack.sh and justfile bash recipes.

export COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-1}"
export BUILDKIT_STEP_MAX_CONCURRENCY="${BUILDKIT_STEP_MAX_CONCURRENCY:-1}"
export NODE_MAX_OLD_SPACE_SIZE="${NODE_MAX_OLD_SPACE_SIZE:-2048}"
export NODE_OPTIONS="--max-old-space-size=${NODE_MAX_OLD_SPACE_SIZE}"
