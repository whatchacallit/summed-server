import logging, uvicorn
from dotenv import find_dotenv, load_dotenv


#
# Load environment variables from the '.env' file
# Make sure you have your credentials there for local development.
# (On Azure, those env vars will be already be set via Application Settings, and we don't override them here)
#
load_dotenv(find_dotenv())

# Standard format for all log messages
log = logging.getLogger(__name__)

# Imports the API (a FastAPI "app")
# FastAPI App and API versions as Sub Applications
# see: https://fastapi.tiangolo.com/advanced/sub-applications/#mounting-a-fastapi-application
import app.api as api


# Entrypoint for "python main.py"
if __name__ == "__main__":

    #
    # Start uvicorn server
    #
    uvicorn.run(api, host="0.0.0.0", port=5000, log_level="debug", log_config=None)
