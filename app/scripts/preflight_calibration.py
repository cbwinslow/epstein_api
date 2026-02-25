#!/usr/bin/env python3
"""
Preflight Calibration Script

Comprehensive system diagnostic tool that verifies all components
before production workloads. Runs async checks on infrastructure,
LLM connectivity, and performs a micro-pipeline simulation.

Usage:
    python backend/scripts/preflight_calibration.py
"""

import asyncio
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import redis.asyncio as redis
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.databases.neo4j_client import Neo4jClient
from backend.core.databases.chroma_client import ChromaDBClient
from backend.core.settings import Settings, get_settings
from backend.agents.fact_extractor import FactExtractor, GraphArchitect
from backend.agents.model_router import ModelRouter


class SidecarData(BaseModel):
    """Minimal sidecar for testing."""

    original_file_id: int
    filename: str
    raw_text: str
    processing_status: str = "completed"
    extracted_text: str = ""
    metadata: dict[str, Any] = {}


@dataclass
class DiagnosticResult:
    """Result of a single diagnostic check."""

    name: str
    status: str  # "pass", "warning", "fail"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class CalibrationReport:
    """Complete calibration report."""

    timestamp: str
    results: list[DiagnosticResult] = field(default_factory=list)

    def add(self, result: DiagnosticResult) -> None:
        self.results.append(result)

    def passes(self) -> list[DiagnosticResult]:
        return [r for r in self.results if r.status == "pass"]

    def warnings(self) -> list[DiagnosticResult]:
        return [r for r in self.results if r.status == "warning"]

    def failures(self) -> list[DiagnosticResult]:
        return [r for r in self.results if r.status == "fail"]


class PreflightCalibration:
    """Main calibration orchestrator."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._report = CalibrationReport(timestamp=datetime.now(timezone.utc).isoformat())

    async def run_all(self) -> CalibrationReport:
        """Run all diagnostic phases."""
        print("=" * 60)
        print("OSINT PLATFORM PRE-FLIGHT CALIBRATION")
        print("=" * 60)
        print()

        await self.phase1_infrastructure()
        await self.phase2_llm_pulse()
        await self.phase3_micro_pipeline()
        self.phase4_generate_report()

        return self._report

    async def phase1_infrastructure(self) -> None:
        """Phase 1: Infrastructure & Environment Probes."""
        print("[PHASE 1] Infrastructure & Environment Probes")
        print("-" * 40)

        await self.check_environment()
        await self.check_redis()
        await self.check_neo4j()
        await self.check_chromadb()
        self.check_binaries()

        print()

    async def check_environment(self) -> None:
        """Verify environment variables exist."""
        start = time.perf_counter()
        required_vars = [
            "OPENROUTER_API_KEY",
            "NEO4J_URI",
            "NEO4J_USERNAME",
            "NEO4J_PASSWORD",
            "REDIS_URL",
        ]

        missing = []
        detected = []

        for var in required_vars:
            value = os.environ.get(var)
            if value:
                detected.append(var)
            else:
                missing.append(var)

        duration = (time.perf_counter() - start) * 1000

        if missing:
            self._report.add(
                DiagnosticResult(
                    name="Environment Variables",
                    status="fail",
                    message=f"Missing required variables: {', '.join(missing)}",
                    details={"missing": missing, "detected": detected},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Environment Variables: {len(missing)} missing")
        else:
            self._report.add(
                DiagnosticResult(
                    name="Environment Variables",
                    status="pass",
                    message="All required environment variables detected",
                    details={"detected": detected},
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] Environment Variables: All {len(detected)} detected")

    async def check_redis(self) -> None:
        """Test Redis connectivity."""
        start = time.perf_counter()
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

        try:
            client = redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            await client.aclose()

            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="Redis Connection",
                    status="pass",
                    message="Redis ping successful",
                    details={"url": redis_url},
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] Redis: Connection successful ({duration:.1f}ms)")
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="Redis Connection",
                    status="fail",
                    message=f"Redis unreachable: {str(e)}",
                    details={"url": redis_url, "error": str(e)},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Redis: {str(e)}")

    async def check_neo4j(self) -> None:
        """Test Neo4j connectivity."""
        start = time.perf_counter()

        try:
            client = Neo4jClient(self._settings)
            result = client.execute_query("RETURN 1 AS test")
            client.close()

            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="Neo4j Connection",
                    status="pass",
                    message="Neo4j query successful",
                    details={"uri": self._settings.neo4j.uri},
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] Neo4j: Connection successful ({duration:.1f}ms)")
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="Neo4j Connection",
                    status="fail",
                    message=f"Neo4j unreachable: {str(e)}",
                    details={"uri": self._settings.neo4j.uri, "error": str(e)},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Neo4j: {str(e)}")

    async def check_chromadb(self) -> None:
        """Test ChromaDB connectivity."""
        start = time.perf_counter()

        try:
            client = ChromaDBClient(self._settings)
            collections = client.list_collections()
            client.close()

            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="ChromaDB Connection",
                    status="pass",
                    message="ChromaDB heartbeat successful",
                    details={"collections": len(collections)},
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] ChromaDB: Connection successful ({duration:.1f}ms)")
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="ChromaDB Connection",
                    status="fail",
                    message=f"ChromaDB unreachable: {str(e)}",
                    details={"error": str(e)},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] ChromaDB: {str(e)}")

    def check_binaries(self) -> None:
        """Check for required system binaries."""
        binaries = ["tesseract", "ffmpeg"]
        found = []
        missing = []

        for binary in binaries:
            path = shutil.which(binary)
            if path:
                found.append({"name": binary, "path": path})
            else:
                missing.append(binary)

        if missing:
            self._report.add(
                DiagnosticResult(
                    name="System Binaries",
                    status="warning",
                    message=f"Missing binaries: {', '.join(missing)}",
                    details={"found": found, "missing": missing},
                )
            )
            print(f"  [WARN] Binaries: {', '.join(missing)} not found")
        else:
            self._report.add(
                DiagnosticResult(
                    name="System Binaries",
                    status="pass",
                    message="All required binaries found",
                    details={"found": found},
                )
            )
            print(f"  [PASS] Binaries: All {len(found)} found")

    async def phase2_llm_pulse(self) -> None:
        """Phase 2: LLM Pulse Check."""
        print("[PHASE 2] LLM Pulse Check")
        print("-" * 40)

        await self.check_openrouter()
        print()

    async def check_openrouter(self) -> None:
        """Ping OpenRouter API with minimal prompt."""
        start = time.perf_counter()
        api_key = os.environ.get("OPENROUTER_API_KEY", "")

        if not api_key:
            self._report.add(
                DiagnosticResult(
                    name="OpenRouter API",
                    status="fail",
                    message="No API key configured",
                    duration_ms=0,
                )
            )
            print(f"  [FAIL] OpenRouter: No API key")
            return

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "google/gemma-2-9b-ite",
                        "messages": [{"role": "user", "content": "Say the word 'calibrated'."}],
                        "max_tokens": 1,
                    },
                )

            duration = (time.perf_counter() - start) * 1000

            if response.status_code == 401:
                self._report.add(
                    DiagnosticResult(
                        name="OpenRouter API",
                        status="fail",
                        message="Unauthorized - Invalid API key",
                        details={"status_code": 401},
                        duration_ms=duration,
                    )
                )
                print(f"  [FAIL] OpenRouter: 401 Unauthorized")
            elif response.status_code == 429:
                self._report.add(
                    DiagnosticResult(
                        name="OpenRouter API",
                        status="warning",
                        message="Rate limited",
                        details={"status_code": 429},
                        duration_ms=duration,
                    )
                )
                print(f"  [WARN] OpenRouter: 429 Rate Limited")
            elif response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens_used = data.get("usage", {}).get("total_tokens", 0)

                self._report.add(
                    DiagnosticResult(
                        name="OpenRouter API",
                        status="pass",
                        message=f"Response received: '{content[:50]}'",
                        details={
                            "status_code": 200,
                            "tokens_used": tokens_used,
                            "model": "google/gemma-2-9b-ite",
                        },
                        duration_ms=duration,
                    )
                )
                print(f"  [PASS] OpenRouter: Response in {duration:.1f}ms")
            else:
                self._report.add(
                    DiagnosticResult(
                        name="OpenRouter API",
                        status="fail",
                        message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                        duration_ms=duration,
                    )
                )
                print(f"  [FAIL] OpenRouter: HTTP {response.status_code}")

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="OpenRouter API",
                    status="fail",
                    message=f"Connection failed: {str(e)}",
                    details={"error": str(e)},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] OpenRouter: {str(e)}")

    async def phase3_micro_pipeline(self) -> None:
        """Phase 3: Micro-Pipeline Simulation."""
        print("[PHASE 3] Micro-Pipeline Simulation (Dry Run)")
        print("-" * 40)

        await self.create_dummy_sidecar()
        await self.test_fact_extractor()
        await self.test_graph_architect()
        print()

    async def create_dummy_sidecar(self) -> None:
        """Create a dummy sidecar for testing."""
        start = time.perf_counter()

        data_dir = Path(self._settings.storage.data_dir)
        processed_dir = data_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        dummy_path = processed_dir / "dummy_calibration_99999.json"

        dummy_data = SidecarData(
            original_file_id=99999,
            filename="dummy_calibration_test.txt",
            raw_text="John Doe met with Jane Smith in New York on 2024-01-01. They discussed business opportunities.",
            processing_status="completed",
        )

        try:
            with open(dummy_path, "w") as f:
                json.dump(dummy_data.model_dump(), f)

            duration = (time.perf_counter() - start) * 1000
            self._dummy_sidecar_path = dummy_path

            self._report.add(
                DiagnosticResult(
                    name="Dummy Sidecar Creation",
                    status="pass",
                    message=f"Created test file: {dummy_path.name}",
                    details={"path": str(dummy_path)},
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] Sidecar: Created dummy file")
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="Dummy Sidecar Creation",
                    status="fail",
                    message=f"Failed to create: {str(e)}",
                    details={"error": str(e)},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] Sidecar: {str(e)}")
            self._dummy_sidecar_path = None

    async def test_fact_extractor(self) -> None:
        """Test the FactExtractor agent."""
        if not self._dummy_sidecar_path:
            self._report.add(
                DiagnosticResult(
                    name="FactExtractor Agent",
                    status="fail",
                    message="Skipped - no dummy sidecar",
                )
            )
            print(f"  [SKIP] FactExtractor: No sidecar")
            return

        start = time.perf_counter()

        try:
            router = ModelRouter(self._settings)
            extractor = FactExtractor(self._settings, router)

            result = await extractor.run(self._dummy_sidecar_path)

            duration = (time.perf_counter() - start) * 1000

            persons = result.get("persons", [])
            locations = result.get("locations", [])

            self._extraction_result = result

            self._report.add(
                DiagnosticResult(
                    name="FactExtractor Agent",
                    status="pass",
                    message=f"Extracted {len(persons)} persons, {len(locations)} locations",
                    details={
                        "persons": len(persons),
                        "locations": len(locations),
                        "organizations": len(result.get("organizations", [])),
                    },
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] FactExtractor: Extracted entities ({duration:.1f}ms)")
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="FactExtractor Agent",
                    status="fail",
                    message=f"Extraction failed: {str(e)}",
                    details={"error": str(e)},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] FactExtractor: {str(e)}")
            self._extraction_result = None

    async def test_graph_architect(self) -> None:
        """Test the GraphArchitect agent."""
        if not self._extraction_result:
            self._report.add(
                DiagnosticResult(
                    name="GraphArchitect Agent",
                    status="fail",
                    message="Skipped - no extraction result",
                )
            )
            print(f"  [SKIP] GraphArchitect: No extraction")
            return

        start = time.perf_counter()

        try:
            router = ModelRouter(self._settings)
            architect = GraphArchitect(self._settings, router)

            test_relationships = [
                {
                    "from_entity": "John Doe",
                    "to_entity": "Jane Smith",
                    "relationship_type": "MET_WITH",
                    "score": 5,
                    "evidence": ["Document states they met"],
                    "confidence": "high",
                }
            ]

            result = await architect.run(test_relationships)

            duration = (time.perf_counter() - start) * 1000

            has_cypher = any(op.get("type") == "merge_relationship" for op in result)

            self._report.add(
                DiagnosticResult(
                    name="GraphArchitect Agent",
                    status="pass" if has_cypher else "fail",
                    message=f"Generated {len(result)} Neo4j operations",
                    details={
                        "operations": len(result),
                        "has_merge": has_cypher,
                    },
                    duration_ms=duration,
                )
            )
            print(f"  [PASS] GraphArchitect: Generated ops ({duration:.1f}ms)")
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._report.add(
                DiagnosticResult(
                    name="GraphArchitect Agent",
                    status="fail",
                    message=f"Operation failed: {str(e)}",
                    details={"error": str(e)},
                    duration_ms=duration,
                )
            )
            print(f"  [FAIL] GraphArchitect: {str(e)}")

    def phase4_generate_report(self) -> None:
        """Generate the calibration report."""
        print("[PHASE 4] Generating Report")
        print("-" * 40)

        base_dir = Path(__file__).parent.parent.parent / "data" / "telemetry" / "reports"
        base_dir.mkdir(parents=True, exist_ok=True)

        report_path = base_dir / "calibration_report.md"

        passes = self._report.passes()
        warnings = self._report.warnings()
        failures = self._report.failures()

        lines = [
            "# OSINT Platform Pre-Flight Calibration Report",
            "",
            f"**Generated:** {self._report.timestamp}",
            "",
            "## Summary",
            "",
            f"| Status | Count |",
            f"|--------|-------|",
            f"| ✅ Pass | {len(passes)} |",
            f"| ⚠️  Warning | {len(warnings)} |",
            f"| ❌ Fail | {len(failures)} |",
            "",
            f"**Overall Status:** {'✅ READY' if not failures else '❌ NOT READY'}",
            "",
            "---",
            "",
            "## Detailed Results",
            "",
        ]

        if passes:
            lines.append("### ✅ Passed")
            lines.append("")
            for r in passes:
                lines.append(f"- **{r.name}**: {r.message} ({r.duration_ms:.1f}ms)")
            lines.append("")

        if warnings:
            lines.append("### ⚠️  Warnings")
            lines.append("")
            for r in warnings:
                lines.append(f"- **{r.name}**: {r.message}")
            lines.append("")

        if failures:
            lines.append("### ❌ Failures")
            lines.append("")
            for r in failures:
                lines.append(f"- **{r.name}**: {r.message}")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "## Recommended Fixes",
                "",
            ]
        )

        if failures or warnings:
            for r in failures + warnings:
                if "Redis" in r.name:
                    lines.append(
                        f"- **Redis**: Ensure Redis is running via Docker: `docker-compose up -d redis`"
                    )
                elif "Neo4j" in r.name:
                    lines.append(
                        f"- **Neo4j**: Ensure Neo4j is running via Docker: `docker-compose up -d neo4j`"
                    )
                elif "ChromaDB" in r.name:
                    lines.append(f"- **ChromaDB**: Check ChromaDB service availability")
                elif "Binaries" in r.name:
                    lines.append(
                        f"- **Binaries**: Install missing tools: `apt-get install tesseract-ocr ffmpeg`"
                    )
                elif "OpenRouter" in r.name:
                    lines.append(f"- **OpenRouter**: Check API key in .env file")
                elif "FactExtractor" in r.name or "GraphArchitect" in r.name:
                    lines.append(f"- **Agents**: Check LLM connectivity and agent configuration")
                else:
                    lines.append(f"- **{r.name}**: Review configuration")
        else:
            lines.append("*No fixes needed - all systems operational.*")

        lines.extend(
            [
                "",
                "---",
                "",
                f"*Report generated by preflight_calibration.py*",
            ]
        )

        report_content = "\n".join(lines)

        with open(report_path, "w") as f:
            f.write(report_content)

        print(f"  [DONE] Report saved to: {report_path}")
        print()
        print("=" * 60)
        print(f"RESULT: {'✅ READY FOR PRODUCTION' if not failures else '❌ FIX FAILURES FIRST'}")
        print("=" * 60)


async def main() -> None:
    """Main entry point."""
    try:
        settings = get_settings()
    except Exception:
        settings = Settings()

    calibration = PreflightCalibration(settings)
    report = await calibration.run_all()

    exit_code = 0 if not report.failures() else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
