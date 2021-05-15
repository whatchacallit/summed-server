import os, logging, requests, uuid
from fastapi.exceptions import HTTPException

from app.api_models import ImmersiveReaderTokenResponse, TranslateResponse

log = logging.getLogger(__name__)


async def translate(text: str, to="de") -> str:
    """
    Translates text to "to".
    """
    subscription_key = os.getenv("AZURE_COGNITIVE_SERVICES_KEY")
    endpoint = os.getenv("AZURE_COGNITIVE_SERVICES_ENDPOINT")
    region = os.getenv("AZURE_COGNITIVE_SERVICES_REGION")

    path = "/translate"
    constructed_url = endpoint + path

    params = {"api-version": "3.0", "to": [to]}

    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Ocp-Apim-Subscription-Region": region,
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }

    body = [{"text": text}]

    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()

    result = [
        {
            "from_language": t["detectedLanguage"]["language"],
            "from_text": text,
            "to_language": t["translations"][0]["to"],
            "to_text": t["translations"][0]["text"],
        }
        for t in response
    ]

    return TranslateResponse(**result[0])


async def transcribe(audio: any, language="en_US") -> str:
    """
    Transcribes text from audio (file, stream...)
    """
    pass


async def ocr(image: any, language="en_US") -> str:
    """
    Extracts text from images
    """
    pass


async def getIRToken():
    """
    Get the auth Token for the Immersive Reader UI component.
    This requires some setup, see:  https://docs.microsoft.com/en-us/azure/cognitive-services/immersive-reader/how-to-create-immersive-reader

    """
    clientId = os.getenv("AZURE_IMMERSIVE_READER_CLIENT_ID")
    clientSecret = os.getenv("AZURE_IMMERSIVE_READER_CLIENT_SECRET")
    # AAD auth endpoint
    tenantId = os.getenv("AZURE_IMMERSIVE_READER_TENANT_ID")
    subdomain = os.getenv("AZURE_IMMERSIVE_READER_SUBDOMAIN")

    resource = "https://cognitiveservices.azure.com/"
    oauthTokenUrl = f"https://login.windows.net/{tenantId}/oauth2/token"
    grantType = "client_credentials"

    try:
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": clientId,
            "client_secret": clientSecret,
            "resource": resource,
            "grant_type": grantType,
        }

        resp = requests.post(
            oauthTokenUrl,
            data=data,
            headers=headers,
        )
        jsonResp = resp.json()

        if "access_token" not in jsonResp:
            print(jsonResp)
            raise HTTPException(
                500,
                "AAD Authentication error. Check your Immersive Reader access credentials",
            )

        token = jsonResp["access_token"]

        return ImmersiveReaderTokenResponse(token=token, subdomain=subdomain)
    except Exception as e:
        message = f"Unable to acquire Azure AD token for Immersive Reader: {str(e)}"
        log.error(message)
        raise HTTPException(500, message)