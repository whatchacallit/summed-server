from app.api import API_V1
from fastapi.middleware.cors import CORSMiddleware

# We might swap out complete api major version implementation, based on setting in the future.
api = API_V1

# CORS origins
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
