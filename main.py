#!/usr/bin/env python3
"""main.py — Start the webhook server."""

import uvicorn
from server.config import PORT, LOG_LEVEL

if __name__ == "__main__":
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level=LOG_LEVEL.lower(),
    )
