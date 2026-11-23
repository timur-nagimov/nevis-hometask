"""`python -m app` serves the API on port 8000 (the CMD of the runtime image)."""

import uvicorn


def main() -> None:
    # One worker, fixed here (uvicorn would otherwise read WEB_CONCURRENCY). uvicorn's own access log is off
    # because it prints the query string, which holds search terms; app.main writes its own access log.
    uvicorn.run("app.main:create_app", factory=True, host="0.0.0.0", port=8000, workers=1, access_log=False)


if __name__ == "__main__":
    main()
