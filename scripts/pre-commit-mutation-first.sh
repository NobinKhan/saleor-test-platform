#!/bin/bash
# Pre-commit hook: Run mutation-first enforcement tests
# This ensures that changes don't break the mutation-first testing framework

set -e

echo "Running mutation-first enforcement tests..."

cd backend

# Run the mutation-first tests
if .venv/bin/python -m pytest tests/test_mutation_first.py -q; then
    echo "✓ Mutation-first enforcement tests passed"
    exit 0
else
    echo "✗ Mutation-first enforcement tests failed"
    echo ""
    echo "The mutation-first testing framework has been broken."
    echo "Please ensure all L1 success probes have setup mutations in probe_setup.py"
    exit 1
fi
