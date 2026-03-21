

import os
import sys
import time
import socket
import platform
import subprocess
import textwrap
import logging
import signal
from pathlib import Path
from typing import Optional

# venv setup
ROOT = Path(__file__).parent.resolve()
VENV_DIR = ROOT / ".venv"

def activate_venv() -> None:
    """Ensure venv site-packages are in sys.path if running via base python."""
    if VENV_DIR.exists():
        # add site-packages to this process
        site_packages = VENV_DIR / "Lib" / "site-packages"
        if site_packages.exists() and str(site_packages) not in sys.path:
            sys.path.insert(0, str(site_packages))
        
        # make sure child processes use this venv
        os.environ["VIRTUAL_ENV"] = str(VENV_DIR)
        os.environ["PYTHONPATH"] = str(site_packages) + os.pathsep + os.environ.get("PYTHONPATH", "")
        
        # keep Scripts on PATH for pip and tools
        scripts_dir = VENV_DIR / "Scripts"
        if scripts_dir.exists():
            os.environ["PATH"] = str(scripts_dir) + os.pathsep + os.environ.get("PATH", "")

activate_venv()

# paths
BACKEND_DIR = ROOT / "backend"
DASHBOARD   = ROOT / "dashboard" / "admin_dashboard.py"
SEED_SCRIPT = ROOT / "scripts" / "seed_data.py"
LOG_DIR     = ROOT / "logs"
LOG_FILE    = LOG_DIR / "app.log"
ENV_FILE    = BACKEND_DIR / ".env"
REQ_FILE    = BACKEND_DIR / "requirements.txt"
PYTHON      = str((VENV_DIR / "Scripts" / "python.exe") if (VENV_DIR / "Scripts" / "python.exe").exists() else Path(sys.executable))

# logging

_handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
if os.environ.get("APP_ENABLE_RUNNER_FILE_LOG", "false").lower() == "true":
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _handlers.append(logging.FileHandler(LOG_FILE, encoding="utf-8"))
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=_handlers,
)
log = logging.getLogger("znshop.runner")

if platform.system() == "Windows":
    try:
        os.system("color")  # enable ANSI colors on Windows
    except Exception:
        pass  # skip if color command is unavailable

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg: str)   -> None: log.info(f"{GREEN}✔{RESET}  {msg}")
def warn(msg: str) -> None: log.warning(f"{YELLOW}⚠{RESET}  {msg}")
def err(msg: str)  -> None: log.error(f"{RED}✖{RESET}  {msg}")
def info(msg: str) -> None: log.info(f"{CYAN}→{RESET}  {msg}")

# track child processes for clean shutdown
_processes: list[subprocess.Popen] = []

def _stop_all(*_) -> None:
    print(f"\n{YELLOW}Shutting down ZnShop…{RESET}")
    for p in _processes:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT,  _stop_all)
signal.signal(signal.SIGTERM, _stop_all)

# python version check
def check_python() -> None:
    if sys.version_info < (3, 10):
        err(f"Python 3.10+ required. You have {sys.version}")
        sys.exit(1)
    ok(f"Python {sys.version.split()[0]}")

# dependency install
def install_dependencies() -> None:
    print("DEBUG: install_dependencies start")
    if not REQ_FILE.exists():
        warn(f"requirements.txt not found at {REQ_FILE}")
        return
    info("Checking/installing dependencies…")
    
    cmd = [PYTHON, "-m", "pip", "install", "-q", "-r", str(REQ_FILE)]

    info(f"Running: {' '.join(map(str, cmd))}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        err(f"Dependency installation failed to launch: {e}")
        raise

    if result.returncode != 0:
        err(f"Dependency installation failed:\n{result.stderr}")
        sys.exit(1)
    ok("Dependencies satisfied")

# env validation
REQUIRED_VARS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SECRET_KEY",
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD",
    "WHATSAPP_VERIFY_TOKEN",
]

def check_env() -> None:
    if not ENV_FILE.exists():
        err(f".env not found at {ENV_FILE}")
        err("Copy backend/.env.example → backend/.env and fill in your values.")
        sys.exit(1)

    # parse .env directly without importing the app
    defined: set[str] = set()
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            defined.add(line.split("=", 1)[0].strip())

    missing = [v for v in REQUIRED_VARS if v not in defined]
    if missing:
        err(f"Missing required .env variables: {', '.join(missing)}")
        sys.exit(1)

    ok(".env validated")

# port and process helpers
def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0

def _wait_for_port(port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_in_use(port):
            return True
        time.sleep(0.5)
    return False

def _launch(name: str, cmd: list[str], cwd: Optional[Path] = None,
            env: Optional[dict] = None) -> subprocess.Popen:
    merged_env = {**os.environ, **(env or {})}
    log.debug(f"Launching {name}: {' '.join(map(str, cmd))}")
    try:
        p = subprocess.Popen(
            cmd,
            cwd=str(cwd or ROOT),
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as e:
        err(f"Failed to launch {name}: {e}\nCommand: {' '.join(map(str, cmd))}")
        raise
    _processes.append(p)
    log.debug(f"Started {name} (PID {p.pid}): {' '.join(cmd)}")
    return p

# redis
def ensure_redis() -> None:
    if _port_in_use(6379):
        ok("Redis already running on :6379")
        return

    info("Starting Redis via Docker…")
    try:
        result = subprocess.run(
            ["docker", "run", "-d", "--rm", "--name", "znshop_redis_standalone",
             "-p", "6379:6379", "redis:7-alpine"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        warn("Docker 'docker' command not found. Skipping Docker-based Redis.")
        result = subprocess.CompletedProcess(args=[], returncode=1)
    if result.returncode != 0:
        warn("Could not start Redis via Docker. Trying redis-server…")
        p = _launch("redis-server", ["redis-server"])
        time.sleep(1.5)
        if not _port_in_use(6379):
            err("Redis is not running and could not be started.")
            err("Install Redis or Docker and try again.")
            sys.exit(1)
    else:
        time.sleep(1.0)

    ok("Redis running on :6379")

# fastapi
def start_fastapi() -> subprocess.Popen:
    if _port_in_use(8000):
        ok("FastAPI already running on :8000 — skipping launch")
        return None

    info("Starting FastAPI on :8000…")
    env_patch = {"PYTHONPATH": str(ROOT)}
    reload_enabled = os.environ.get("ZNSHOP_RELOAD", "false").lower() == "true"
    cmd = [PYTHON, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    if reload_enabled:
        cmd.append("--reload")

    p = _launch(
        "fastapi",
        cmd,
        cwd=ROOT,
        env=env_patch,
    )
    if not _wait_for_port(8000, timeout=20):
        if p.poll() is not None:
            try:
                output = p.stdout.read() if p.stdout else ""
            except Exception:
                output = ""
            err("FastAPI process exited before startup.")
            if output:
                err(f"FastAPI output:\n{output[-2000:]}")
        else:
            err("FastAPI did not start within 20 s.")
        sys.exit(1)
    ok("FastAPI running → http://localhost:8000")
    return p

# celery worker
def start_celery() -> subprocess.Popen:
    info("Starting Celery worker…")
    env_patch = {"PYTHONPATH": str(ROOT)}
    p = _launch(
        "celery",
        [PYTHON, "-m", "celery", "-A", "backend.app.workers.celery_app",
         "worker", "--loglevel=info", "--concurrency=2"],
        cwd=ROOT,
        env=env_patch,
    )
    time.sleep(2)
    ok("Celery worker started")
    return p

# ollama check
def check_ollama() -> None:
    if _port_in_use(11434):
        ok("Ollama running on :11434")
    else:
        warn("Ollama is NOT running on :11434.")
        warn("AI intent parsing will fail. Run `ollama serve` && `ollama pull mistral`.")

# seed demo data
def seed_demo_data() -> tuple[int, int]:
    if not SEED_SCRIPT.exists():
        warn(f"Seed script not found: {SEED_SCRIPT}")
        return 0, 0

    info("Seeding demo data…")
    result = subprocess.run(
        [PYTHON, str(SEED_SCRIPT)],
        capture_output=True, text=True,
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        warn(f"Seed script exited with errors — may be a duplicate-data warning:\n{result.stderr[:400]}")
    else:
        ok("Demo data seeded")

    stores  = result.stdout.count("[ok]   stores")  + result.stdout.count("[skip] stores")
    vendors = result.stdout.count("[ok]   vendors") + result.stdout.count("[skip] vendors")
    return stores or 4, vendors or 6

# admin dashboard
def start_dashboard() -> Optional[subprocess.Popen]:
    if not DASHBOARD.exists():
        warn(f"Dashboard not found: {DASHBOARD}")
        return None

    if _port_in_use(8501):
        ok("Admin dashboard already running on :8501 — skipping launch")
        return None

    info("Starting Admin Dashboard on :8501…")
    p = _launch(
        "streamlit",
        [PYTHON, "-m", "streamlit", "run", str(DASHBOARD),
         "--server.port", "8501",
         "--server.address", "0.0.0.0",
         "--server.headless", "true"],
    )
    if _wait_for_port(8501, timeout=15):
        ok("Admin Dashboard → http://localhost:8501")
    else:
        warn("Dashboard may not be ready yet — check if streamlit is installed")
    return p

# summary banner
def _read_env_var(key: str) -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{key}=") and not line.startswith("#"):
            return line.split("=", 1)[1].strip()
    return "—"

def print_banner(stores: int, vendors: int) -> None:
    admin_email    = _read_env_var("ADMIN_EMAIL")
    admin_password = _read_env_var("ADMIN_PASSWORD")
    banner = textwrap.dedent(f"""
    {BOLD}{GREEN}╔══════════════════════════════════════════════════╗
    ║         ZnShop System Started ✔                  ║
    ╚══════════════════════════════════════════════════╝{RESET}

    {CYAN}Services{RESET}
      API          → http://localhost:8000
      Docs         → http://localhost:8000/docs
      Admin REST   → http://localhost:8000/api/v1/admin
      Dashboard    → http://localhost:8501

    {CYAN}Demo Admin{RESET}
      Email        : {admin_email}
      Password     : {admin_password}

    {CYAN}Demo Data{RESET}
      Stores       : {stores}  (Ravi Kirana · Gupta General Store · Lakshmi Store · Patel Mart)
      Vendors      : {vendors}  (Milk · Maggi · Rice · Tea · Biscuit · Oil)

    {CYAN}Quick test commands{RESET}
      Health       : curl http://localhost:8000/health
      Docs         : open http://localhost:8000/docs in browser
      Admin login  : curl -X POST http://localhost:8000/api/v1/admin/login \\
                          -H "Content-Type: application/json" \\
                          -d '{{"email":"{admin_email}","password":"{admin_password}"}}'
      Run tests    : python -m pytest tests/ -v

    {YELLOW}Press Ctrl+C to stop all services.{RESET}
    """)
    print(banner)

# log tail loop
def tail_logs() -> None:
    """Stream FastAPI stdout to the console until Ctrl+C."""
    api_proc = next((p for p in _processes if p is not None), None)
    if not api_proc:
        # no stream yet, keep process alive
        while True:
            time.sleep(1)
        return

    for line in api_proc.stdout:  # type: ignore[union-attr]
        sys.stdout.write(line)
        sys.stdout.flush()

# main
def main() -> None:
    print(f"\n{BOLD}ZnShop — Starting up…{RESET}\n")

    check_python()
    install_dependencies()
    check_env()
    ensure_redis()
    start_fastapi()
    start_celery()
    check_ollama()
    stores, vendors = seed_demo_data()
    start_dashboard()
    print_banner(stores, vendors)
    tail_logs()


if __name__ == "__main__":
    main()
