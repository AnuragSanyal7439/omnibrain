"""Local launcher for the OmniBrain FastAPI app.

Use this from VS Code or the terminal instead of running app/main.py directly.
"""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
