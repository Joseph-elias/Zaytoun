.PHONY: perf-preflight perf-phase0 perf-phase0-safe

perf-preflight:
	powershell -ExecutionPolicy Bypass -File backend/scripts/perf_preflight.ps1

perf-phase0:
	powershell -ExecutionPolicy Bypass -File backend/scripts/run_phase0_e2e.ps1

perf-phase0-safe:
	powershell -ExecutionPolicy Bypass -File backend/scripts/run_phase0_safe.ps1
