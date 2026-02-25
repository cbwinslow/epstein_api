#!/usr/bin/env python3
"""
Master Orchestrator for Epstein OSINT Pipeline.

Eliminates "tick-tack" environment errors through comprehensive pre-flight
checks, intelligent service orchestration, and post-flight validation.

Usage:
    python orchestrate.py
"""

import asyncio
import os
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""

    name: str
    status: str
    message: str
    fix_command: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class OrchestratorReport:
    """Complete orchestrator report."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)

    def passes(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == "pass"]

    def warnings(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == "warning"]

    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == "fail"]


class MasterOrchestrator:
    """Main orchestrator for the OSINT pipeline."""

    PORTS = {
        6379: ("redis", "Redis"),
        7474: ("neo4j", "Neo4j HTTP"),
        7687: ("neo4j", "Neo4j Bolt"),
        8000: ("chromadb", "ChromaDB"),
        3000: ("frontend", "Frontend"),
    }

    REQUIRED_DIRS = [
        ("data/raw", "Raw data directory"),
        ("data/processed", "Processed data directory"),
        ("backend/logs", "Backend logs directory"),
    ]

    def __init__(self) -> None:
        self._report = OrchestratorReport()
        self._config: dict[str, Any] = {}
        self._root_dir = Path(__file__).parent.resolve()

    async def run(self) -> OrchestratorReport:
        """Execute the full orchestration pipeline."""
        print("=" * 70)
        print("MASTER ORCHESTRATOR - EPSTEIN OSINT PIPELINE")
        print("=" * 70)
        print()

        await self.phase1_deep_context_audit()
        await self.phase2_doctor_pre_flight()
        await self.phase3_launch_services()
        await self.phase4_validation_post_flight()

        self._print_summary()
        return self._report

    async def phase1_deep_context_audit(self) -> None:
        """Phase 1: Deep Context Audit."""
        print("[PHASE 1] Deep Context Audit")
        print("-" * 50)

        await self.check_config_yaml()
        await self.check_gpu_configuration()
        await self.check_schemas_compatibility()

        print()

    async def check_config_yaml(self) -> None:
        """Load and validate config.yaml."""
        start = time.perf_counter()

        config_path = self._root_dir / "backend" / "config.yaml"

        try:
            with open(config_path) as f:
                self._config = yaml.safe_load(f)

            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                CheckResult(
                    name="Config YAML",
                    status="pass",
                    message="config.yaml loaded successfully",
                    details={"version": self._config.get("app", {}).get("version")},
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] Config YAML: Loaded successfully")

        except FileNotFoundError:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                CheckResult(
                    name="Config YAML",
                    status="fail",
                    message="config.yaml not found",
                    fix_command="Ensure backend/config.yaml exists",
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Config YAML: Not found")

        except yaml.YAMLError as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                CheckResult(
                    name="Config YAML",
                    status="fail",
                    message=f"YAML parse error: {str(e)}",
                    fix_command="Validate YAML syntax in backend/config.yaml",
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Config YAML: Parse error")

    async def check_gpu_configuration(self) -> None:
        """Verify NVIDIA Container Toolkit if GPU is enabled."""
        start = time.perf_counter()

        use_gpu = os.environ.get("USE_GPU", "false").lower() == "true"

        if not use_gpu and self._config:
            app_config = self._config.get("app", {})
            use_gpu = app_config.get("use_gpu", False)

        if not use_gpu:
            self._report.add(
                CheckResult(
                    name="GPU Configuration",
                    status="pass",
                    message="GPU not enabled - skipping NVIDIA check",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
            )
            print(f"  [SKIP] GPU: Not enabled")
            return

        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                timeout=10,
            )

            if result.returncode == 0:
                self._report.add(
                    CheckResult(
                        name="GPU Configuration",
                        status="pass",
                        message="NVIDIA GPU detected",
                        duration_ms=(time.perf_counter() - start) * 1000,
                    )
                )
                print(f"  [PASS] GPU: NVIDIA GPU detected")

            else:
                self._report.add(
                    CheckResult(
                        name="GPU Configuration",
                        status="fail",
                        message="NVIDIA GPU not accessible",
                        fix_command="Install NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html",
                        duration_ms=(time.perf_counter() - start) * 1000,
                    )
                )
                print(f"  [FAIL] GPU: Not accessible")

        except FileNotFoundError:
            self._report.add(
                CheckResult(
                    name="GPU Configuration",
                    status="fail",
                    message="nvidia-smi not found",
                    fix_command="Install NVIDIA drivers and Container Toolkit",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
            )
            print(f"  [FAIL] GPU: nvidia-smi not found")

        except subprocess.TimeoutExpired:
            self._report.add(
                CheckResult(
                    name="GPU Configuration",
                    status="fail",
                    message="nvidia-smi timed out",
                    fix_command="Check NVIDIA driver installation",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
            )
            print(f"  [FAIL] GPU: nvidia-smi timeout")

    async def check_schemas_compatibility(self) -> None:
        """Validate schemas.py data types are supported locally."""
        start = time.perf_counter()

        schemas_path = self._root_dir / "backend" / "core" / "processing" / "schemas.py"

        if not schemas_path.exists():
            self._report.add(
                CheckResult(
                    name="Schemas Compatibility",
                    status="fail",
                    message="schemas.py not found",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
            )
            print(f"  [FAIL] Schemas: Not found")
            return

        try:
            with open(schemas_path) as f:
                content = f.read()

            required_types = ["datetime", "Enum", "BaseModel"]
            missing_types = [t for t in required_types if t not in content]

            fact_extractor_import = "FactExtractor" in content
            graph_architect_import = "GraphArchitect" in content

            duration = (time.perf_counter() - start) * 1000

            if missing_types:
                self._report.add(
                    CheckResult(
                        name="Schemas Compatibility",
                        status="fail",
                        message=f"Missing required types: {', '.join(missing_types)}",
                        fix_command="Install pydantic: uv add pydantic",
                        duration_ms=duration,
                    )
                )
                print(f"  [FAIL] Schemas: Missing types")
            elif not fact_extractor_import or not graph_architect_import:
                self._report.add(
                    CheckResult(
                        name="Schemas Compatibility",
                        status="warning",
                        message="FactExtractor/GraphArchitect not in schemas.py",
                        duration_ms=duration,
                    )
                )
                print(f"  [WARN] Schemas: Agent references not found")
            else:
                self._report.add(
                    CheckResult(
                        name="Schemas Compatibility",
                        status="pass",
                        message="Schemas compatible with local environment",
                        duration_ms=duration,
                    )
                )
                print(f"  [PASS] Schemas: Compatible")

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                CheckResult(
                    name="Schemas Compatibility",
                    status="fail",
                    message=f"Error reading schemas: {str(e)}",
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Schemas: Error - {str(e)}")

    async def phase2_doctor_pre_flight(self) -> None:
        """Phase 2: The Doctor Logic (Pre-Flight)."""
        print("[PHASE 2] Doctor Logic (Pre-Flight)")
        print("-" * 50)

        await self.check_port_conflicts()
        await self.ensure_directories()
        await self.check_dependencies()

        print()

    async def check_port_conflicts(self) -> None:
        """Check for port conflicts with native Ubuntu services."""
        occupied_ports: dict[int, tuple[str, str | None]] = {}

        for port, (service, name) in self.PORTS.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:
                process = self._get_process_on_port(port)
                occupied_ports[port] = (name, process)

        duration = 0.0

        if occupied_ports:
            fix_commands = []
            for port, (name, process) in occupied_ports.items():
                if process and "redis" in process.lower():
                    fix_commands.append(
                        f"sudo systemctl stop redis-server  # Free port {port}"
                    )
                elif process and "neo4j" in process.lower():
                    fix_commands.append(
                        f"sudo systemctl stop neo4j  # Free port {port}"
                    )

            self._report.add(
                CheckResult(
                    name="Port Conflicts",
                    status="warning",
                    message=f"Ports occupied: {', '.join(str(p) for p in occupied_ports.keys())}",
                    fix_command="; ".join(fix_commands)
                    if fix_commands
                    else "Stop conflicting services",
                    details={
                        str(port): {"service": n, "process": p}
                        for port, (n, p) in occupied_ports.items()
                    },
                    duration_ms=duration,
                )
            )
            for port, (name, process) in occupied_ports.items():
                print(f"  [WARN] Port {port} ({name}): {process or 'occupied'}")
        else:
            self._report.add(
                CheckResult(
                    name="Port Conflicts",
                    status="pass",
                    message="All required ports available",
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] Ports: All available")

    def _get_process_on_port(self, port: int) -> str | None:
        """Get process name using port."""
        try:
            result = subprocess.run(
                ["ss", "-tlnp", f"sport = :{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                match = re.search(r"pid=(\d+)", result.stdout)
                if match:
                    pid = match.group(1)
                    proc_result = subprocess.run(
                        ["ps", "-p", pid, "-o", "comm="],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    return (
                        proc_result.stdout.strip()
                        if proc_result.returncode == 0
                        else None
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    async def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        created = []
        existing = []
        failed = []

        for dir_path, description in self.REQUIRED_DIRS:
            full_path = self._root_dir / dir_path
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                if not any(full_path.iterdir()) if full_path.exists() else True:
                    created.append(dir_path)
                else:
                    existing.append(dir_path)
            except Exception as e:
                failed.append((dir_path, str(e)))

        duration = 0.0

        if failed:
            self._report.add(
                CheckResult(
                    name="Directory Integrity",
                    status="fail",
                    message=f"Failed to create directories: {[d for d, _ in failed]}",
                    duration_ms=duration,
                )
            )
            for d, e in failed:
                print(f"  [FAIL] Directory {d}: {e}")
        else:
            self._report.add(
                CheckResult(
                    name="Directory Integrity",
                    status="pass",
                    message=f"All directories ready ({len(created)} created, {len(existing)} existing)",
                    details={"created": created, "existing": existing},
                    duration_ms=duration,
                )
            )
            for d in created:
                print(f"  [PASS] Directory {d}: Created")
            for d in existing:
                print(f"  [PASS] Directory {d}: Exists")

    async def check_dependencies(self) -> None:
        """Verify docker, docker-compose (V2), and uv are active."""
        dependencies = {
            "docker": ["docker", "--version"],
            "docker-compose": ["docker", "compose", "version"],
            "uv": ["uv", "--version"],
        }

        results: dict[str, bool] = {}

        for name, cmd in dependencies.items():
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=10,
                    cwd=self._root_dir,
                )
                results[name] = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                results[name] = False

        duration = 0.0

        failed = [k for k, v in results.items() if not v]

        if failed:
            fixes = {
                "docker": "Install Docker: https://docs.docker.com/engine/install/",
                "docker-compose": "Install Docker Compose V2: docker compose install",
                "uv": "Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh",
            }

            self._report.add(
                CheckResult(
                    name="Dependency Check",
                    status="fail",
                    message=f"Missing: {', '.join(failed)}",
                    fix_command="; ".join(fixes[f] for f in failed),
                    duration_ms=duration,
                )
            )
            for name, available in results.items():
                status = "PASS" if available else "FAIL"
                print(f"  [{status}] {name}")
        else:
            self._report.add(
                CheckResult(
                    name="Dependency Check",
                    status="pass",
                    message="All dependencies available",
                    details={k: v for k, v in results.items()},
                    duration_ms=duration,
                )
            )
            for name, available in results.items():
                print(f"  [PASS] {name}")

    async def phase3_launch_services(self) -> None:
        """Phase 3: The Launch Logic."""
        print("[PHASE 3] Launch Services")
        print("-" * 50)

        await self.docker_compose_up()
        await self.socket_wait_loop()

        print()

    async def docker_compose_up(self) -> None:
        """Orchestrate docker compose up."""
        start = time.perf_counter()

        compose_file = self._root_dir / "docker-compose.yml"

        if not compose_file.exists():
            self._report.add(
                CheckResult(
                    name="Docker Compose",
                    status="fail",
                    message="docker-compose.yml not found",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
            )
            print(f"  [FAIL] Docker Compose: File not found")
            return

        try:
            result = subprocess.run(
                ["docker", "compose", "up", "-d", "--remove-orphans"],
                capture_output=True,
                text=True,
                cwd=self._root_dir,
                timeout=300,
            )

            duration = (time.perf_counter() - start) * 1000

            if result.returncode == 0:
                self._report.add(
                    CheckResult(
                        name="Docker Compose",
                        status="pass",
                        message="Services started successfully",
                        details={"stdout": result.stdout[:500]},
                        duration_ms=duration,
                    )
                )
                print(f"  [PASS] Docker Compose: Services started")
            else:
                self._report.add(
                    CheckResult(
                        name="Docker Compose",
                        status="fail",
                        message=f"Failed to start services: {result.stderr[:200]}",
                        fix_command="Check docker-compose.yml and logs: docker compose logs",
                        details={"stderr": result.stderr[:500]},
                        duration_ms=duration,
                    )
                )
                print(f"  [FAIL] Docker Compose: {result.stderr[:100]}")

        except subprocess.TimeoutExpired:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                CheckResult(
                    name="Docker Compose",
                    status="fail",
                    message="Docker compose timed out",
                    fix_command="Check docker daemon status: sudo systemctl status docker",
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Docker Compose: Timeout")

        except FileNotFoundError:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                CheckResult(
                    name="Docker Compose",
                    status="fail",
                    message="Docker not installed",
                    fix_command="Install Docker: https://docs.docker.com/engine/install/",
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Docker Compose: Docker not found")

    async def socket_wait_loop(self) -> None:
        """Wait for services to become available using socket connections."""
        services = {
            "Redis": ("localhost", 6379),
            "Neo4j Bolt": ("localhost", 7687),
            "Neo4j HTTP": ("localhost", 7474),
            "ChromaDB": ("localhost", 8000),
        }

        timeout = 120
        poll_interval = 2
        start_time = time.time()
        ready: dict[str, bool] = {name: False for name in services}
        final_status: dict[str, str] = {}

        print(f"  Waiting for services (timeout: {timeout}s)...")

        while time.time() - start_time < timeout:
            all_ready = True

            for name, (host, port) in services.items():
                if ready[name]:
                    continue

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)

                try:
                    result = sock.connect_ex((host, port))
                    sock.close()

                    if result == 0:
                        ready[name] = True
                        final_status[name] = "pass"
                        print(f"    {name}: Ready")
                except Exception:
                    all_ready = False

            if all_ready:
                break

            await asyncio.sleep(poll_interval)

        duration = (time.time() - start_time) * 1000

        failed = [name for name, status in final_status.items() if status != "pass"]

        if failed:
            self._report.add(
                CheckResult(
                    name="Service Availability",
                    status="fail",
                    message=f"Services not ready: {', '.join(failed)}",
                    fix_command="Check docker compose logs: docker compose logs",
                    details={"ready": ready, "timeout": timeout},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Services: {', '.join(failed)} not ready")
        else:
            self._report.add(
                CheckResult(
                    name="Service Availability",
                    status="pass",
                    message="All services available",
                    details={"services": list(services.keys())},
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] Services: All available ({duration / 1000:.1f}s)")

    async def phase4_validation_post_flight(self) -> None:
        """Phase 4: The Validation Logic (Post-Flight)."""
        print("[PHASE 4] Validation (Post-Flight)")
        print("-" * 50)

        await self.run_preflight_calibration()

        print()

    async def run_preflight_calibration(self) -> None:
        """Run the preflight calibration script inside the worker container."""
        start = time.perf_counter()

        calibration_script = (
            self._root_dir / "backend" / "scripts" / "preflight_calibration.py"
        )

        if not calibration_script.exists():
            self._report.add(
                CheckResult(
                    name="Preflight Calibration",
                    status="fail",
                    message="preflight_calibration.py not found",
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
            )
            print(f"  [FAIL] Calibration: Script not found")
            return

        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "epstein-worker",
                    "bash",
                    "-c",
                    "cd /app && uv run python scripts/preflight_calibration.py",
                ],
                capture_output=True,
                text=True,
                cwd=self._root_dir,
                timeout=300,
                env={**os.environ, "TERM": "xterm"},
            )

            duration = (time.perf_counter() - start) * 1000

            if result.returncode == 0:
                self._report.add(
                    CheckResult(
                        name="Preflight Calibration",
                        status="pass",
                        message="Calibration passed",
                        details={"output": result.stdout[-500:]},
                        duration_ms=duration,
                    )
                )
                print(f"  [PASS] Calibration: Passed")
            else:
                error_msg = result.stderr or result.stdout
                fix_suggestion = self._parse_calibration_failure(error_msg)

                self._report.add(
                    CheckResult(
                        name="Preflight Calibration",
                        status="fail",
                        message=f"Calibration failed: {error_msg[:200]}",
                        fix_command=fix_suggestion,
                        details={
                            "stdout": result.stdout[-500:],
                            "stderr": result.stderr[-500:],
                        },
                        duration_ms=duration,
                    )
                )
                print(f"  [FAIL] Calibration: Failed")
                print(f"    Suggestion: {fix_suggestion}")

        except subprocess.TimeoutExpired:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                CheckResult(
                    name="Preflight Calibration",
                    status="fail",
                    message="Calibration timed out",
                    fix_command="Check worker container logs: docker logs epstein-worker",
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Calibration: Timeout")

        except FileNotFoundError:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                CheckResult(
                    name="Preflight Calibration",
                    status="fail",
                    message="Worker container not running",
                    fix_command="Start worker: docker compose up -d worker",
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Calibration: Worker not running")

    def _parse_calibration_failure(self, error_output: str) -> str:
        """Parse calibration failure and suggest specific fixes."""
        error_lower = error_output.lower()

        if "redis" in error_lower and "connection" in error_lower:
            return (
                "Check Redis: docker compose logs redis; docker compose restart redis"
            )

        if "neo4j" in error_lower and (
            "connection" in error_lower or "auth" in error_lower
        ):
            return "Check Neo4j: docker compose logs neo4j; Verify credentials in config.yaml"

        if "chromadb" in error_lower and "connection" in error_lower:
            return "Check ChromaDB: docker compose logs chromadb; docker compose restart chromadb"

        if "openrouter" in error_lower:
            return "Set OPENROUTER_API_KEY in .env file: https://openrouter.ai/settings"

        if "environment" in error_lower and "variable" in error_lower:
            return "Set required environment variables in .env file"

        if "factextractor" in error_lower or "grapharchitect" in error_lower:
            return "Check LLM configuration and agent setup in backend/config.yaml"

        if "nvidia" in error_lower or "gpu" in error_lower:
            return "Verify NVIDIA Container Toolkit: nvidia-smi; Check docker compose GPU config"

        return "Review full logs: docker compose logs --tail=100"

    def _print_summary(self) -> None:
        """Print the final summary."""
        passes = self._report.passes()
        warnings = self._report.warnings()
        failures = self._report.failures()

        print("=" * 70)
        print("ORCHESTRATION SUMMARY")
        print("=" * 70)
        print(f"  ✅ Pass: {len(passes)}")
        print(f"  ⚠️  Warning: {len(warnings)}")
        print(f"  ❌ Fail: {len(failures)}")
        print()

        if failures:
            print("Failures requiring attention:")
            for f in failures:
                print(f"  - {f.name}: {f.message}")
                if f.fix_command:
                    print(f"    → Fix: {f.fix_command}")
            print()
            print("❌ ORCHESTRATION FAILED - Fix failures before proceeding")
        elif warnings:
            print("⚠️  ORCHESTRATION COMPLETED WITH WARNINGS")
        else:
            print("✅ ORCHESTRATION COMPLETED SUCCESSFULLY")

        print("=" * 70)


async def main() -> None:
    """Main entry point."""
    orchestrator = MasterOrchestrator()
    report = await orchestrator.run()

    exit_code = 1 if report.failures() else 0
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
