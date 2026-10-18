"""`python -m app` starts the server on http://127.0.0.1:8000."""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=os.environ.get("DEVNEXUS_HOST", "127.0.0.1"),
        port=int(os.environ.get("DEVNEXUS_PORT", "8000")),
    )
