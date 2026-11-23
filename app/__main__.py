import uvicorn

from app.config import Settings
from app.main import create_app


def main() -> None:
    settings = Settings()
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        workers=1,
        access_log=False,  # the application writes its own access log
        log_config=None,  # uvicorn's lines, 500 tracebacks included, go through the application's format
    )


if __name__ == '__main__':
    main()
