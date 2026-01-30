"""
Standalone tests for scaffold-foundry-app scenarios.

These tests validate the scaffolder prompt output patterns without requiring
acceptance criteria (which is only available for skills, not prompts).

The scaffolder is a PROMPT (.github/prompts/scaffold-foundry-app.prompt.md),
not a SKILL, so it cannot be discovered by the main harness which requires
both acceptance-criteria.md and scenarios.yaml.

Run with:
    pytest tests/test_scaffolder.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml


SCENARIOS_FILE = Path(__file__).parent / "scenarios" / "scaffold-foundry-app" / "scenarios.yaml"


@pytest.fixture(scope="module")
def scenarios_data() -> dict:
    """Load the scaffolder scenarios YAML file."""
    if not SCENARIOS_FILE.exists():
        pytest.skip(f"Scenarios file not found: {SCENARIOS_FILE}")

    with open(SCENARIOS_FILE) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def scenarios(scenarios_data: dict) -> list[dict]:
    """Extract the list of scenarios from the YAML data."""
    return scenarios_data.get("scenarios", [])


def get_scenario_names(scenarios_file: Path) -> list[str]:
    """Get all scenario names for parametrization."""
    if not scenarios_file.exists():
        return []

    with open(scenarios_file) as f:
        data = yaml.safe_load(f)

    return [s["name"] for s in data.get("scenarios", [])]


# =============================================================================
# Pattern Validation Tests
# =============================================================================


class TestScaffolderScenarios:
    """Test that mock responses match expected/forbidden patterns."""

    @pytest.mark.parametrize("scenario_name", get_scenario_names(SCENARIOS_FILE))
    def test_scenario_expected_patterns(self, scenarios: list[dict], scenario_name: str):
        """Verify mock response contains all expected patterns."""
        scenario = next((s for s in scenarios if s["name"] == scenario_name), None)
        assert scenario is not None, f"Scenario '{scenario_name}' not found"

        mock_response = scenario.get("mock_response", "")
        expected_patterns = scenario.get("expected_patterns", [])

        missing_patterns = []
        for pattern in expected_patterns:
            # Use regex search for flexibility
            if not re.search(re.escape(pattern), mock_response):
                missing_patterns.append(pattern)

        assert not missing_patterns, (
            f"Scenario '{scenario_name}' mock_response missing expected patterns:\n"
            f"  {missing_patterns}"
        )

    @pytest.mark.parametrize("scenario_name", get_scenario_names(SCENARIOS_FILE))
    def test_scenario_forbidden_patterns(self, scenarios: list[dict], scenario_name: str):
        """Verify mock response does NOT contain forbidden patterns."""
        scenario = next((s for s in scenarios if s["name"] == scenario_name), None)
        assert scenario is not None, f"Scenario '{scenario_name}' not found"

        mock_response = scenario.get("mock_response", "")
        forbidden_patterns = scenario.get("forbidden_patterns", [])

        found_forbidden = []
        for pattern in forbidden_patterns:
            if re.search(re.escape(pattern), mock_response):
                found_forbidden.append(pattern)

        assert not found_forbidden, (
            f"Scenario '{scenario_name}' mock_response contains forbidden patterns:\n"
            f"  {found_forbidden}"
        )


# =============================================================================
# Scenario Structure Tests
# =============================================================================


class TestScenarioStructure:
    """Test that scenarios are well-formed."""

    def test_scenarios_file_exists(self):
        """Scenarios file should exist."""
        assert SCENARIOS_FILE.exists(), f"Missing: {SCENARIOS_FILE}"

    def test_scenarios_not_empty(self, scenarios: list[dict]):
        """Should have at least one scenario."""
        assert len(scenarios) > 0, "No scenarios defined"

    def test_all_scenarios_have_required_fields(self, scenarios: list[dict]):
        """Each scenario should have required fields."""
        required_fields = {"name", "prompt", "mock_response"}

        for scenario in scenarios:
            missing = required_fields - set(scenario.keys())
            assert not missing, (
                f"Scenario '{scenario.get('name', 'UNNAMED')}' missing fields: {missing}"
            )

    def test_all_scenarios_have_patterns(self, scenarios: list[dict]):
        """Each scenario should have at least expected_patterns or forbidden_patterns."""
        for scenario in scenarios:
            has_expected = bool(scenario.get("expected_patterns"))
            has_forbidden = bool(scenario.get("forbidden_patterns"))

            assert has_expected or has_forbidden, (
                f"Scenario '{scenario['name']}' has no expected_patterns or forbidden_patterns"
            )

    def test_scenario_names_are_unique(self, scenarios: list[dict]):
        """Scenario names should be unique."""
        names = [s["name"] for s in scenarios]
        duplicates = [name for name in names if names.count(name) > 1]

        assert not duplicates, f"Duplicate scenario names: {set(duplicates)}"

    def test_all_scenarios_have_tags(self, scenarios: list[dict]):
        """Each scenario should have at least one tag."""
        for scenario in scenarios:
            tags = scenario.get("tags", [])
            assert len(tags) > 0, f"Scenario '{scenario['name']}' has no tags"


# =============================================================================
# Infrastructure Scenarios
# =============================================================================


class TestInfrastructureScenarios:
    """Tests for infrastructure-related scaffolder scenarios."""

    def test_azure_yaml_has_remote_build(self, scenarios: list[dict]):
        """azure.yaml should use remoteBuild: true."""
        scenario = next((s for s in scenarios if s["name"] == "azure_yaml_config"), None)
        if scenario is None:
            pytest.skip("azure_yaml_config scenario not found")

        mock = scenario["mock_response"]
        assert "remoteBuild: true" in mock, "azure.yaml should use remoteBuild: true"

    def test_azure_yaml_has_container_apps(self, scenarios: list[dict]):
        """azure.yaml should use Container Apps host."""
        scenario = next((s for s in scenarios if s["name"] == "azure_yaml_config"), None)
        if scenario is None:
            pytest.skip("azure_yaml_config scenario not found")

        mock = scenario["mock_response"]
        assert "host: containerapp" in mock, "azure.yaml should use Container Apps"

    def test_bicep_has_managed_identity(self, scenarios: list[dict]):
        """Bicep should use managed identity, not admin credentials."""
        scenario = next((s for s in scenarios if s["name"] == "bicep_main_module"), None)
        if scenario is None:
            pytest.skip("bicep_main_module scenario not found")

        mock = scenario["mock_response"]
        assert "managedIdentity" in mock, "Bicep should reference managed identity"
        assert "password" not in mock.lower(), "Bicep should not contain passwords"


# =============================================================================
# Backend Scenarios
# =============================================================================


class TestBackendScenarios:
    """Tests for FastAPI backend scaffolder scenarios."""

    def test_fastapi_uses_lifespan(self, scenarios: list[dict]):
        """FastAPI main.py should use lifespan for resource management."""
        scenario = next((s for s in scenarios if s["name"] == "fastapi_main"), None)
        if scenario is None:
            pytest.skip("fastapi_main scenario not found")

        mock = scenario["mock_response"]
        assert "@asynccontextmanager" in mock, "Should use asynccontextmanager"
        assert "async def lifespan" in mock, "Should define lifespan function"

    def test_fastapi_has_health_endpoint(self, scenarios: list[dict]):
        """FastAPI should have a health check endpoint."""
        scenario = next((s for s in scenarios if s["name"] == "fastapi_main"), None)
        if scenario is None:
            pytest.skip("fastapi_main scenario not found")

        mock = scenario["mock_response"]
        assert "/health" in mock, "Should have /health endpoint"

    def test_pyproject_has_required_deps(self, scenarios: list[dict]):
        """pyproject.toml should include required dependencies."""
        scenario = next((s for s in scenarios if s["name"] == "pyproject_toml"), None)
        if scenario is None:
            pytest.skip("pyproject_toml scenario not found")

        mock = scenario["mock_response"]
        required = ["fastapi", "pydantic", "pytest", "ruff", "azure-identity"]

        for dep in required:
            assert dep in mock, f"pyproject.toml should include {dep}"

    def test_pydantic_uses_v2_patterns(self, scenarios: list[dict]):
        """Pydantic models should use v2 patterns, not v1."""
        scenario = next((s for s in scenarios if s["name"] == "pydantic_models"), None)
        if scenario is None:
            pytest.skip("pydantic_models scenario not found")

        mock = scenario["mock_response"]

        # V2 patterns
        assert "from pydantic import BaseModel" in mock, "Should import BaseModel"

        # V1 anti-patterns (should NOT be present)
        assert "class Config:" not in mock, "Should not use Pydantic v1 Config class"
        assert "orm_mode" not in mock, "Should not use Pydantic v1 orm_mode"


# =============================================================================
# Frontend Scenarios
# =============================================================================


class TestFrontendScenarios:
    """Tests for React/Vite frontend scaffolder scenarios."""

    def test_vite_uses_esm(self, scenarios: list[dict]):
        """Vite config should use ES modules."""
        scenario = next((s for s in scenarios if s["name"] == "vite_config"), None)
        if scenario is None:
            pytest.skip("vite_config scenario not found")

        mock = scenario["mock_response"]
        assert "import { defineConfig }" in mock, "Should use ESM imports"
        assert "module.exports" not in mock, "Should not use CommonJS"

    def test_package_json_has_fluent_ui_v9(self, scenarios: list[dict]):
        """package.json should use Fluent UI v9, not v8."""
        scenario = next((s for s in scenarios if s["name"] == "package_json"), None)
        if scenario is None:
            pytest.skip("package_json scenario not found")

        mock = scenario["mock_response"]
        assert '"@fluentui/react-components"' in mock, "Should use Fluent UI v9"
        assert '"@fluentui/react":' not in mock, "Should not use Fluent UI v8"

    def test_app_uses_dark_theme(self, scenarios: list[dict]):
        """App.tsx should use webDarkTheme, not light theme."""
        scenario = next((s for s in scenarios if s["name"] == "fluent_theme_provider"), None)
        if scenario is None:
            pytest.skip("fluent_theme_provider scenario not found")

        mock = scenario["mock_response"]
        assert "webDarkTheme" in mock, "Should use webDarkTheme"
        assert "FluentProvider" in mock, "Should use FluentProvider"
        assert "webLightTheme" not in mock, "Should not use light theme"

    def test_tsconfig_is_strict(self, scenarios: list[dict]):
        """tsconfig.json should have strict mode enabled."""
        scenario = next((s for s in scenarios if s["name"] == "tsconfig_strict"), None)
        if scenario is None:
            pytest.skip("tsconfig_strict scenario not found")

        mock = scenario["mock_response"]
        assert '"strict": true' in mock, "Should have strict: true"
        assert '"strict": false' not in mock, "Should not have strict: false"


# =============================================================================
# Container Scenarios
# =============================================================================


class TestContainerScenarios:
    """Tests for Docker/container scaffolder scenarios."""

    def test_backend_dockerfile_uses_uv(self, scenarios: list[dict]):
        """Backend Dockerfile should use uv, not pip."""
        scenario = next((s for s in scenarios if s["name"] == "dockerfile_backend"), None)
        if scenario is None:
            pytest.skip("dockerfile_backend scenario not found")

        mock = scenario["mock_response"]
        assert "uv" in mock, "Should use uv"
        assert "RUN pip install" not in mock, "Should not use pip install"
        assert "requirements.txt" not in mock, "Should not use requirements.txt"

    def test_frontend_dockerfile_uses_pnpm(self, scenarios: list[dict]):
        """Frontend Dockerfile should use pnpm, not npm/yarn."""
        scenario = next((s for s in scenarios if s["name"] == "dockerfile_frontend"), None)
        if scenario is None:
            pytest.skip("dockerfile_frontend scenario not found")

        mock = scenario["mock_response"]
        assert "pnpm" in mock, "Should use pnpm"
        assert "RUN npm install" not in mock, "Should not use npm install"
        assert "yarn" not in mock, "Should not use yarn"

    def test_frontend_dockerfile_uses_nginx(self, scenarios: list[dict]):
        """Frontend Dockerfile should serve with nginx."""
        scenario = next((s for s in scenarios if s["name"] == "dockerfile_frontend"), None)
        if scenario is None:
            pytest.skip("dockerfile_frontend scenario not found")

        mock = scenario["mock_response"]
        assert "nginx" in mock, "Should use nginx for serving"


# =============================================================================
# Tag Coverage Tests
# =============================================================================


class TestTagCoverage:
    """Verify scenarios cover all expected categories."""

    def test_has_infrastructure_scenarios(self, scenarios: list[dict]):
        """Should have infrastructure-tagged scenarios."""
        infra_scenarios = [s for s in scenarios if "infrastructure" in s.get("tags", [])]
        assert len(infra_scenarios) >= 2, "Should have at least 2 infrastructure scenarios"

    def test_has_backend_scenarios(self, scenarios: list[dict]):
        """Should have backend-tagged scenarios."""
        backend_scenarios = [s for s in scenarios if "backend" in s.get("tags", [])]
        assert len(backend_scenarios) >= 2, "Should have at least 2 backend scenarios"

    def test_has_frontend_scenarios(self, scenarios: list[dict]):
        """Should have frontend-tagged scenarios."""
        frontend_scenarios = [s for s in scenarios if "frontend" in s.get("tags", [])]
        assert len(frontend_scenarios) >= 2, "Should have at least 2 frontend scenarios"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
