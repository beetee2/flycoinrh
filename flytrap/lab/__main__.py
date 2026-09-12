"""Start only the bounded loopback prototype."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("flytrap.lab.api:create_lab_app", factory=True, host="127.0.0.1", port=8766,
                workers=1, limit_concurrency=16, timeout_keep_alive=5)
