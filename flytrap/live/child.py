"""Linux parent-death guard, installed before exec without threaded preexec_fn."""
import ctypes
import os
import signal
import sys


def command(arguments):
    return [sys.executable, "-m", "flytrap.live.child", str(os.getpid()), *arguments]


def main():
    parent = int(sys.argv[1])
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG
        raise OSError(ctypes.get_errno(), "parent-death guard unavailable")
    # Covers death between Popen and prctl. The signal survives exec.
    if os.getppid() != parent:
        return 2
    os.execvpe(sys.argv[2], sys.argv[2:], os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
