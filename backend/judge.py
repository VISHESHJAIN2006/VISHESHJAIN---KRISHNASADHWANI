"""
Code execution / judging engine.

Demo-scope sandbox: this uses subprocess isolation with CPU/time/memory/process
limits (via `resource`), a scratch temp directory, and a stripped environment.
It is NOT equivalent to the microVM/container isolation (Firecracker/gVisor)
called for in the production architecture doc (see §7 of the blueprint) --
running arbitrary untrusted code with only subprocess-level limits is not
safe for a real multi-tenant deployment. Treat this as a working reference
implementation of the Judge Service's *interface and judging logic*, to be
swapped onto real sandboxed workers for production use.
"""
import subprocess
import tempfile
import os
import platform

IS_WINDOWS = platform.system() == "Windows"

if not IS_WINDOWS:
    import resource
import textwrap

# --- Language registry --------------------------------------------------
# Adding a language = adding an entry here. Nothing else in the judge
# needs to change, mirroring the "config-driven language registry" from
# the architecture doc (§4.3).

LANGUAGE_REGISTRY = {
    "python": {
        "label": "Python 3",
        "filename": "solution.py",
        "run_cmd": lambda path, memory_mb: ["python", path],
        # CPython's own memory footprint tracks its actual usage closely, so a
        # hard virtual-memory ceiling (RLIMIT_AS) is a meaningful, enforceable limit.
        "enforce_as_limit": True,
        "default_starter": textwrap.dedent("""\
            import sys

            def solve(input_text: str) -> str:
                # Read from input_text, return the output string.
                lines = input_text.strip().split("\\n")
                return ""

            if __name__ == "__main__":
                data = sys.stdin.read()
                print(solve(data))
            """),
    },
    "javascript": {
        "label": "JavaScript (Node.js)",
        "filename": "solution.js",
        # V8 reserves a large virtual address range up front regardless of actual
        # usage, so RLIMIT_AS reliably OOM-kills Node on startup. Cap the V8 heap
        # via its own flag instead, and rely on RLIMIT_CPU + the wall-clock
        # subprocess timeout for the rest.
        "run_cmd": lambda path, memory_mb: ["node", f"--max-old-space-size={memory_mb}", path],
        "enforce_as_limit": False,
        "default_starter": textwrap.dedent("""\
            function solve(inputText) {
              // Read from inputText, return the output string.
              const lines = inputText.trim().split("\\n");
              return "";
            }

            const chunks = [];
            process.stdin.on("data", (d) => chunks.push(d));
            process.stdin.on("end", () => {
              console.log(solve(chunks.join("")));
            });
            """),
    },
}

MAX_MEMORY_BYTES = 256 * 1024 * 1024  # hard ceiling regardless of per-problem setting
MAX_CPU_SECONDS = 10                  # hard ceiling regardless of per-problem time limit


def _limit_resources(memory_mb, cpu_seconds, enforce_as_limit):
    if IS_WINDOWS:
        return None
    def _apply():
        cpu = min(cpu_seconds, MAX_CPU_SECONDS)
        if enforce_as_limit:
            mem_bytes = min(memory_mb * 1024 * 1024, MAX_MEMORY_BYTES)
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
        try:
            os.setsid()
        except AttributeError:
            pass
    return _apply


def run_single(language, source_code, stdin_text, time_limit_ms=2000, memory_limit_mb=256):
    """
    Runs `source_code` once against `stdin_text`.
    Returns dict: {status, stdout, stderr, runtime_ms}
    status in {OK, TLE, MLE, RUNTIME_ERROR, COMPILE_ERROR, INTERNAL_ERROR}
    """
    if language not in LANGUAGE_REGISTRY:
        return {"status": "INTERNAL_ERROR", "stdout": "", "stderr": f"Unsupported language: {language}", "runtime_ms": 0}

    lang = LANGUAGE_REGISTRY[language]
    time_limit_s = max(time_limit_ms / 1000.0, 0.5)

    with tempfile.TemporaryDirectory(prefix="judge_") as tmp:
        src_path = os.path.join(tmp, lang["filename"])
        with open(src_path, "w") as f:
            f.write(source_code)

        cmd = lang["run_cmd"](src_path, memory_limit_mb)
        env = os.environ.copy()

        import time
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_text,
                capture_output=True,
                text=True,
                timeout=time_limit_s,
                cwd=tmp,
                env=env,
                preexec_fn=None if IS_WINDOWS else _limit_resources(
                    memory_limit_mb,
                    int(time_limit_s) + 1,
                    lang.get("enforce_as_limit", True),
                ),
            )
            runtime_ms = int((time.monotonic() - start) * 1000)
        except subprocess.TimeoutExpired:
            runtime_ms = int((time.monotonic() - start) * 1000)
            return {"status": "TLE", "stdout": "", "stderr": "Time limit exceeded", "runtime_ms": runtime_ms}
        except Exception as e:
            return {"status": "INTERNAL_ERROR", "stdout": "", "stderr": str(e), "runtime_ms": 0}

        if proc.returncode != 0:
            # MemoryError / RLIMIT_AS violations usually surface as non-zero exit + stderr
            stderr_lower = (proc.stderr or "").lower()
            if "memoryerror" in stderr_lower or "cannot allocate memory" in stderr_lower:
                return {"status": "MLE", "stdout": proc.stdout, "stderr": proc.stderr, "runtime_ms": runtime_ms}
            return {"status": "RUNTIME_ERROR", "stdout": proc.stdout, "stderr": proc.stderr, "runtime_ms": runtime_ms}

        return {"status": "OK", "stdout": proc.stdout, "stderr": proc.stderr, "runtime_ms": runtime_ms}


def _normalize(text):
    return "\n".join(line.rstrip() for line in (text or "").strip("\n").split("\n")).strip()


def judge_submission(language, source_code, test_cases):
    """
    test_cases: list of dicts with keys: id, input_payload, expected_output,
                is_sample, time_limit_ms, memory_limit_mb
    Returns: (overall_status, results_list, total_runtime_ms)
    """
    results = []
    overall_status = "ACCEPTED"
    total_runtime = 0

    for tc in test_cases:
        outcome = run_single(
            language,
            source_code,
            tc["input_payload"],
            tc.get("time_limit_ms", 2000),
            tc.get("memory_limit_mb", 256),
        )
        total_runtime += outcome["runtime_ms"]

        if outcome["status"] != "OK":
            passed = False
            tc_status = outcome["status"]
        else:
            passed = _normalize(outcome["stdout"]) == _normalize(tc["expected_output"])
            tc_status = "ACCEPTED" if passed else "WRONG_ANSWER"

        results.append({
            "test_case_id": tc["id"],
            "is_sample": bool(tc.get("is_sample")),
            "passed": passed,
            "status": tc_status,
            "runtime_ms": outcome["runtime_ms"],
            "stderr_excerpt": (outcome["stderr"] or "")[:500],
            "actual_output_excerpt": (outcome["stdout"] or "")[:500] if tc.get("is_sample") else None,
        })

        if not passed and overall_status == "ACCEPTED":
            overall_status = tc_status

    return overall_status, results, total_runtime
