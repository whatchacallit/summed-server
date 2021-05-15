from fastapi.middleware.cors import CORSMiddleware
import os, logging
from sys import stderr

LOG_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)-20s %(message)s"


def init_api(api, log):
    """
    Initalizes the FastAPI object.
    Middleware and logging, basically
    """
    origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # Add CORS middleware
    api.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    ## Configure the logging for the app
    @api.on_event("startup")
    async def startup_event():
        """ """
        # Additional handlers for logging to file / log mgmt solution
        plain_formatter = logging.Formatter(LOG_FORMAT)
        # FIXME find a working(!) ANSI code console formatter (colorlog didnt qwork for me in VS code terminal)
        console_formatter = logging.Formatter(LOG_FORMAT)

        # Apply to root logger
        app_root_logger = logging.getLogger("app")
        app_root_logger.setLevel(os.getenv("LOGLEVEL", logging.INFO))

        uvicorn_log = logging.getLogger("uvicorn")

        # Create new handlers and set our standardized formatter
        # TODO: use log forwarding to a centralized log mgmt solution / syslog
        logfile_handler = logging.FileHandler("./.server.log")
        logfile_handler.setFormatter(plain_formatter)
        console_handler = logging.StreamHandler(stream=stderr)
        console_handler.setFormatter(console_formatter)

        # App level log messages should go to stdout/stderr too
        app_root_logger.addHandler(console_handler)
        app_root_logger.addHandler(logfile_handler)
        log.addHandler(console_handler)
        log.addHandler(logfile_handler)
        uvicorn_log.addHandler(console_handler)
        uvicorn_log.addHandler(logfile_handler)

        # We're done here...
        log.info(f"Started {api.title} , version={api.version}")

        @api.on_event("shutdown")
        async def shutdown_event():
            log.info(f"Shutting down {api.title}")
