import uvicorn

from fraudguard.core.config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "fraudguard.api.app:create_app",
        factory=True,
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
