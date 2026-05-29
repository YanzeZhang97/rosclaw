"""Entry point: python -m rosclaw.dashboard"""

import uvicorn

from .web_server import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
