#!/usr/bin/env python3
"""
WhatsApp Archive - Development & Deployment Script
===================================================

A single entry point for all project operations.

CONFIGURATION
-------------
Set WH_ARCH_ENV_FILE environment variable to your config file:
    export WH_ARCH_ENV_FILE=/path/to/your/config.env

Or create a .env file in the project root:
    cp .env.example .env

USAGE
-----
    python start.py <command>
    ./start.py <command>  (if executable)

COMMANDS
--------
    init      - First-time setup: install dependencies, create database tables
    backend   - Start the backend API server (port 8000)
    frontend  - Start the frontend dev server (port 5173)
    dev       - Start both backend and frontend for development
    check     - Verify configuration and dependencies
    help      - Show this help message

EXAMPLES
--------
    python start.py init                                    # First time setup
    python start.py dev                                     # Start development servers
    python start.py backend                                 # Start only backend
    WH_ARCH_ENV_FILE=/path/to/.env python start.py dev     # Use custom config
"""

import os
import sys
import subprocess
import shutil
import signal
from pathlib import Path
from typing import Optional, Tuple
import argparse

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR / "backend"
FRONTEND_DIR = SCRIPT_DIR / "frontend"
ENV_VAR_NAME = "WH_ARCH_ENV_FILE"

# Colors (ANSI escape codes)
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    BOLD = "\033[1m"
    NC = "\033[0m"  # No Color

    @classmethod
    def disable(cls):
        """Disable colors (e.g., for non-TTY output)"""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.BOLD = cls.NC = ""


# Disable colors if not a TTY
if not sys.stdout.isatty():
    Colors.disable()


# =============================================================================
# Output Helpers
# =============================================================================

def print_header():
    print()
    print(f"{Colors.BLUE}{'━' * 60}{Colors.NC}")
    print(f"{Colors.BLUE}  WhatsApp Archive{Colors.NC}")
    print(f"{Colors.BLUE}{'━' * 60}{Colors.NC}")
    print()


def print_success(message: str):
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str):
    print(f"{Colors.RED}✗{Colors.NC} {message}")


def print_warning(message: str):
    print(f"{Colors.YELLOW}!{Colors.NC} {message}")


def print_info(message: str):
    print(f"{Colors.BLUE}→{Colors.NC} {message}")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{title}{Colors.NC}")


# =============================================================================
# Configuration Loading
# =============================================================================

def find_config_file() -> Optional[Path]:
    """Find configuration file. Priority: env var > .env in project root"""

    # Check environment variable
    env_file = os.environ.get(ENV_VAR_NAME)
    if env_file:
        path = Path(env_file)
        if path.exists():
            return path
        print_warning(f"{ENV_VAR_NAME} is set but file not found: {env_file}")

    # Check .env in project root
    local_env = SCRIPT_DIR / ".env"
    if local_env.exists():
        return local_env

    return None


def load_config() -> bool:
    """Load environment variables from config file."""
    config_file = find_config_file()

    if not config_file:
        print_error("No configuration file found!")
        print()
        print("Options:")
        print("  1. Create .env file:")
        print("     cp .env.example .env")
        print()
        print(f"  2. Set {ENV_VAR_NAME} environment variable:")
        print(f"     export {ENV_VAR_NAME}=/path/to/your/config.env")
        print()
        return False

    print_info(f"Loading config from: {config_file}")

    # Parse and load environment variables
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse key=value
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                os.environ[key] = value

    return True


# =============================================================================
# Dependency Checks
# =============================================================================

def check_command(name: str) -> Tuple[bool, str]:
    """Check if a command exists and return its version."""
    path = shutil.which(name)
    if not path:
        return False, "not found"

    try:
        if name == "python3":
            result = subprocess.run([name, "--version"], capture_output=True, text=True)
            version = result.stdout.strip().split()[-1]
        elif name == "node":
            result = subprocess.run([name, "--version"], capture_output=True, text=True)
            version = result.stdout.strip()
        elif name == "npm":
            result = subprocess.run([name, "--version"], capture_output=True, text=True)
            version = result.stdout.strip()
        else:
            version = "found"
        return True, version
    except Exception as e:
        return False, str(e)


def check_python() -> bool:
    found, version = check_command("python3")
    if found:
        print_success(f"Python: {version}")
    else:
        print_error(f"Python 3: {version}")
    return found


def check_node() -> bool:
    found, version = check_command("node")
    if found:
        print_success(f"Node.js: {version}")
    else:
        print_error(f"Node.js: {version}")
    return found


def check_npm() -> bool:
    found, version = check_command("npm")
    if found:
        print_success(f"npm: {version}")
    else:
        print_error(f"npm: {version}")
    return found


def check_postgres() -> bool:
    """Check PostgreSQL connection."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print_error("DATABASE_URL not set")
        return False

    try:
        import asyncio
        import asyncpg

        async def test_connection():
            # Convert SQLAlchemy URL to asyncpg format
            url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(url)
            await conn.close()
            return True

        asyncio.run(test_connection())
        print_success("PostgreSQL: connected")
        return True
    except ImportError:
        print_warning("PostgreSQL: asyncpg not installed (run init first)")
        return False
    except Exception as e:
        print_error(f"PostgreSQL: {e}")
        return False


def check_minio() -> bool:
    """Check MinIO connection."""
    endpoint = os.environ.get("MINIO_ENDPOINT")
    if not endpoint:
        print_error("MINIO_ENDPOINT not set")
        return False

    try:
        import urllib.request
        url = f"http://{endpoint}/minio/health/live"
        urllib.request.urlopen(url, timeout=5)
        print_success(f"MinIO: reachable at {endpoint}")
        return True
    except Exception:
        print_warning(f"MinIO: cannot reach {endpoint} (may still work)")
        return True  # Non-critical


def check_backend_deps() -> bool:
    """Check if backend dependencies are installed."""
    try:
        import fastapi
        import sqlalchemy
        import minio
        print_success("Backend dependencies: installed")
        return True
    except ImportError:
        print_warning("Backend dependencies: not fully installed")
        print("         Run: python start.py init")
        return False


def check_frontend_deps() -> bool:
    """Check if frontend dependencies are installed."""
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        print_success("Frontend dependencies: installed")
        return True
    else:
        print_warning("Frontend dependencies: not installed")
        print("         Run: python start.py init")
        return False


# =============================================================================
# Commands
# =============================================================================

def cmd_help():
    """Show help message."""
    print(__doc__)


def cmd_check():
    """Verify configuration and dependencies."""
    print_header()
    print("Checking configuration and dependencies...")

    if not load_config():
        return 1

    print_section("System")
    check_python()
    check_node()
    check_npm()

    print_section("Services")
    check_postgres()
    check_minio()

    print_section("Project")
    check_backend_deps()
    check_frontend_deps()

    print()
    return 0


def cmd_init():
    """First-time setup: install dependencies, create database tables."""
    print_header()
    print("Initializing WhatsApp Archive...")

    if not load_config():
        return 1

    print_section("Checking system requirements")
    if not check_python():
        return 1
    if not check_node():
        return 1

    # Install backend dependencies
    print_section("Installing backend dependencies")
    venv_dir = BACKEND_DIR / "venv"

    if not venv_dir.exists():
        print_info("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    pip_path = venv_dir / "bin" / "pip"
    print_info("Installing Python packages...")
    subprocess.run(
        [str(pip_path), "install", "-q", "-r", str(BACKEND_DIR / "requirements.txt")],
        check=True
    )
    print_success("Backend dependencies installed")

    # Install frontend dependencies
    print_section("Installing frontend dependencies")
    print_info("Installing npm packages...")
    subprocess.run(["npm", "install", "--silent"], cwd=FRONTEND_DIR, check=True)
    print_success("Frontend dependencies installed")

    # Initialize database
    print_section("Initializing database")
    python_path = venv_dir / "bin" / "python"

    init_script = '''
import asyncio
import sys
sys.path.insert(0, ".")
from app.database import init_db

async def setup():
    await init_db()
    print("Database tables created")

asyncio.run(setup())
'''

    subprocess.run(
        [str(python_path), "-c", init_script],
        cwd=BACKEND_DIR,
        check=True
    )
    print_success("Database initialized")

    # MinIO bucket info
    print()
    print_info("MinIO bucket will be created automatically on first run")

    print()
    print_success("Initialization complete!")
    print()
    print("Next steps:")
    print("  python start.py dev      # Start development servers")
    print("  python start.py backend  # Start backend only")
    print()

    return 0


def cmd_backend():
    """Start the backend API server."""
    print_header()

    if not load_config():
        return 1

    print()

    # Determine uvicorn path
    venv_uvicorn = BACKEND_DIR / "venv" / "bin" / "uvicorn"
    if venv_uvicorn.exists():
        uvicorn_cmd = str(venv_uvicorn)
    else:
        uvicorn_cmd = "uvicorn"

    print_info("Starting backend server...")
    print(f"         URL: http://localhost:8000")
    print(f"         API docs: http://localhost:8000/docs")
    print()

    os.chdir(BACKEND_DIR)
    os.execvp(uvicorn_cmd, [uvicorn_cmd, "app.main:app", "--reload", "--port", "8000"])


def cmd_frontend():
    """Start the frontend dev server."""
    print_header()
    print()

    print_info("Starting frontend server...")
    print(f"         URL: http://localhost:5173")
    print()

    os.chdir(FRONTEND_DIR)
    os.execvp("npm", ["npm", "run", "dev"])


def cmd_dev():
    """Start both backend and frontend for development."""
    print_header()

    if not load_config():
        return 1

    print()
    print_info("Starting development servers...")
    print()

    # Track child processes
    processes = []

    def cleanup(signum=None, frame=None):
        print()
        print_info("Stopping services...")
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=5)
            except:
                p.kill()
        sys.exit(0)

    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start backend
    venv_uvicorn = BACKEND_DIR / "venv" / "bin" / "uvicorn"
    if venv_uvicorn.exists():
        uvicorn_cmd = str(venv_uvicorn)
    else:
        uvicorn_cmd = "uvicorn"

    backend_proc = subprocess.Popen(
        [uvicorn_cmd, "app.main:app", "--reload", "--port", "8000"],
        cwd=BACKEND_DIR
    )
    processes.append(backend_proc)

    # Wait a moment for backend
    import time
    time.sleep(2)

    # Start frontend
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR
    )
    processes.append(frontend_proc)

    print()
    print(f"{Colors.GREEN}Services running:{Colors.NC}")
    print(f"  Backend:  http://localhost:8000 (PID: {backend_proc.pid})")
    print(f"  Frontend: http://localhost:5173 (PID: {frontend_proc.pid})")
    print(f"  API Docs: http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop all services")
    print()

    # Wait for processes
    try:
        while True:
            # Check if any process has died
            for p in processes:
                if p.poll() is not None:
                    print_warning(f"Process {p.pid} exited with code {p.returncode}")
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

    return 0


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="WhatsApp Archive - Development & Deployment Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  init      First-time setup: install dependencies, create database tables
  backend   Start the backend API server (port 8000)
  frontend  Start the frontend dev server (port 5173)
  dev       Start both backend and frontend for development
  check     Verify configuration and dependencies
  help      Show detailed help message

Examples:
  python start.py init                                    # First time setup
  python start.py dev                                     # Start dev servers
  WH_ARCH_ENV_FILE=/path/to/.env python start.py dev     # Custom config
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=["init", "backend", "frontend", "dev", "check", "help"],
        help="Command to run"
    )

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "backend": cmd_backend,
        "frontend": cmd_frontend,
        "dev": cmd_dev,
        "check": cmd_check,
        "help": cmd_help,
    }

    cmd_func = commands.get(args.command, cmd_help)

    try:
        result = cmd_func()
        sys.exit(result if result else 0)
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print()
        sys.exit(0)
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
