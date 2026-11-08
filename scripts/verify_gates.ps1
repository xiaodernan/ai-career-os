#!/usr/bin/env pwsh
<#
Runs a representative set of fast, offline contract/gate checks (source/doc/config).
Does not run Docker-dependent *IT, Playwright E2E, or full application test suites.

Usage (from repo root):
  pwsh -File scripts/verify_gates.ps1
  # or on Windows PowerShell:
  powershell -ExecutionPolicy Bypass -File scripts/verify_gates.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root "ai-service\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$tests = @(
  "ai-service/tests/test_every_internal_route_requires_internal_auth.py",
  "ai-service/tests/test_every_internal_route_refuses_unauthenticated.py",
  "ai-service/tests/test_every_internal_route_requires_user_id.py",
  "ai-service/tests/test_the_route_inventory_is_fully_documented_in_openapi.py",
  "ai-service/tests/test_every_openapi_operation_is_described.py",
  "ai-service/tests/test_api_route_paths_are_well_formed.py",
  "ai-service/tests/test_backend_security_config_contract.py",
  "ai-service/tests/test_backend_actuator_exposure_is_minimal.py",
  "ai-service/tests/test_backend_application_config_invariants.py",
  "ai-service/tests/test_require_internal_uses_constant_time_compare.py",
  "ai-service/tests/test_ai_service_main_safety_invariants.py",
  "ai-service/tests/test_deployment_doc_matches_compose_ports.py",
  "ai-service/tests/test_env_prod_example_covers_compose_requirements.py",
  "ai-service/tests/test_env_prod_example_uses_placeholders_for_secrets.py",
  "ai-service/tests/test_prod_compose_does_not_publish_data_ports.py",
  "ai-service/tests/test_prod_compose_services_have_restart_policy.py",
  "ai-service/tests/test_flyway_migrations_follow_naming_convention.py",
  "ai-service/tests/test_ci_referenced_paths_and_modules_exist.py",
  "ai-service/tests/test_readme_and_deployment_doc_links_resolve.py",
  "ai-service/tests/test_quality_gates_doc_exists_and_has_structure.py",
  "ai-service/tests/test_json_log_formatter_carries_request_id.py",
  "ai-service/tests/test_rate_limit_filter_is_wired.py",
  "ai-service/tests/test_journey_api_propagates_request_id.py",
  "ai-service/tests/test_prod_compose_images_are_not_latest.py",
  "ai-service/tests/test_dockerfiles_run_as_non_root.py"
)

Write-Host "== verify_gates: representative offline contract gates =="
& $py -m pytest @tests -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "== OK: representative gates passed (not a substitute for full suites / *IT / E2E) =="
