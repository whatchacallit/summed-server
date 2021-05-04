import os, logging, uvicorn
from sys import stdout, stderr
from dotenv import find_dotenv, load_dotenv


#
# Load environment variables from the '.env' file
# Make sure you have your credentials there for local development.
# (On Azure, those env vars will be already be set via Application Settings, and we don't override them here)
#
load_dotenv(find_dotenv())

# Standard format for all log messages
LOG_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)-35s %(message)s"
log = logging.getLogger(__name__)
log.setLevel(os.environ.get("LOGLEVEL", logging.INFO))

# Imports the API (a FastAPI "app")
# FastAPI App and API versions as Sub Applications
# see: https://fastapi.tiangolo.com/advanced/sub-applications/#mounting-a-fastapi-application
import app.api as api

## Configure the logging for the app
@api.on_event("startup")
async def startup_event():
    # Additional handlers for logging to file / log mgmt solution
    plain_formatter = logging.Formatter(LOG_FORMAT)
    # FIXME find a working(!) ANSI code console formatter (colorlog didnt qwork for me in VS code terminal)
    console_formatter = logging.Formatter(LOG_FORMAT)

    # Apply to root logger
    app_root_logger = logging.getLogger("app")
    app_root_logger.setLevel(os.environ.get("LOGLEVEL", logging.INFO))

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
    log.info(f"Started SumMed API server, version={api.version}")


@api.on_event("shutdown")
async def shutdown_event():
    log.info(f"Shutting down SumMed API server")


# Entrypoint for "python main.py"
if __name__ == "__main__":

    #
    # Start uvicorn server
    #
    uvicorn.run(api, host="0.0.0.0", port=5000, log_level="debug", log_config=None)
