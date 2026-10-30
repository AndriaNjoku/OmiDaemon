"""Windows background service & daemon manager for OmiDaemon."""

import os
import sys
import subprocess
import signal
from pathlib import Path
from typing import Dict, Any, Optional


class DaemonService:
    def __init__(self, pid_file: str = "data/omidaemon.pid", log_file: str = "logs/omidaemon.log"):
        self.pid_file = Path(pid_file).resolve()
        self.log_file = Path(log_file).resolve()
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def is_running(self) -> Tuple_IsRunning:
        """Check if daemon is currently running. Returns (is_running, pid)."""
        if not self.pid_file.exists():
            return False, None
        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            return False, None

        # Verify process existence on Windows
        if os.name == "nt":
            try:
                # Use tasklist or os.kill(pid, 0)
                cmd = ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"]
                out = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if str(pid) in out.stdout:
                    return True, pid
            except Exception:
                pass
        else:
            try:
                os.kill(pid, 0)
                return True, pid
            except OSError:
                pass

        # Stale PID file
        try:
            self.pid_file.unlink()
        except OSError:
            pass
        return False, None

    def start_background(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Launch OmiDaemon detached in the background using pythonw."""
        running, existing_pid = self.is_running()
        if running:
            return {"status": "already_running", "pid": existing_pid, "log": str(self.log_file)}

        # Find pythonw.exe on Windows for windowless execution
        py_executable = sys.executable
        if os.name == "nt":
            pythonw = Path(py_executable).with_name("pythonw.exe")
            if pythonw.exists():
                py_executable = str(pythonw)

        cmd = [py_executable, "-m", "omidaemon.cli", "start"]
        if config_path:
            cmd.extend(["--config", config_path])

        log_handle = open(self.log_file, "a", encoding="utf-8")

        # Windows detached process flags
        creationflags = 0
        if os.name == "nt":
            # DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200)
            creationflags = 0x00000008 | 0x00000200

        proc = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=(os.name != "nt"),
        )

        self.pid_file.write_text(str(proc.pid), encoding="utf-8")
        return {"status": "started", "pid": proc.pid, "log": str(self.log_file)}

    def stop_background(self) -> Dict[str, Any]:
        """Stop running background daemon."""
        running, pid = self.is_running()
        if not running or not pid:
            return {"status": "not_running"}

        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, check=False)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as e:
            return {"status": "error", "error": str(e), "pid": pid}

        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except OSError:
            pass

        return {"status": "stopped", "pid": pid}

    def install_startup_task(self) -> Dict[str, Any]:
        """Register a Windows Scheduled Task to run OmiDaemon at user logon."""
        if os.name != "nt":
            return {"status": "unsupported", "error": "Startup task only supported on Windows"}

        task_name = "OmiDaemon"
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        exec_path = str(pythonw if pythonw.exists() else sys.executable)
        cwd = str(Path.cwd().resolve())

        # Command: pythonw.exe -m omidaemon.cli start
        action_arg = f'"{exec_path}" -m omidaemon.cli start'

        cmd = [
            "schtasks",
            "/Create",
            "/F",
            "/TN",
            task_name,
            "/TR",
            action_arg,
            "/SC",
            "ONLOGON",
            "/RL",
            "LIMITED",
        ]

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return {"status": "installed", "task_name": task_name}
        else:
            return {"status": "failed", "error": res.stderr.strip() or res.stdout.strip()}


# Type alias for clarity
Tuple_IsRunning = tuple[bool, Optional[int]]
