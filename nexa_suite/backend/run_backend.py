import sys
import uvicorn

from app.core.config import get_settings
from app.main import app


def main() -> None:
    settings = get_settings()
    frozen = bool(getattr(sys, "frozen", False))

    uvicorn.run(
        app if frozen else "app.main:app",
        host=settings.backend_host,
        port=int(settings.backend_port),
        reload=settings.app_env == "development" and not frozen,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
