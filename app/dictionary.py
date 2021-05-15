import os, requests, logging, urllib
from fastapi.exceptions import HTTPException
from app.api_models import DefinitionResponse, TermDefinition
from pprint import pprint
from urllib.request import pathname2url

log = logging.getLogger(__name__)


def lookup_term(term: str) -> DefinitionResponse:
    apiKey = os.getenv("MW_API_KEY", None)
    if not apiKey:
        raise HTTPException(
            500,
            "Server configuration error: please configure a valid API key for querying dictionary",
        )

    sanitized_term = pathname2url(term.strip())  # urlencode(term.strip())
    url = f"https://www.dictionaryapi.com/api/v3/references/medical/json/{sanitized_term}?key={apiKey}"
    log.info(f"Looking up term definition via dictionary: {sanitized_term}")

    resp = requests.get(url)
    # pprint(resp.content)

    resp.raise_for_status()
    try:

        if resp.ok:
            jsonResp = resp.json()
            if type(jsonResp[0]) == str:
                # Term not found? -> jsonResp contains just a list of "suggestions" as strings
                definitions = [
                    TermDefinition(
                        **{
                            "id": f"{s}",
                            "term": f"{s}",
                            "type": f"suggestion",
                            "text": f"suggestion: {s}",
                        }
                    )
                    for s in jsonResp
                ]
            else:
                # Term found ? -> jsonResp contains awkward format from MW dictionary API
                definitions = [
                    TermDefinition(
                        **{
                            "id": f"{d['meta']['id']}",
                            "term": f"{d['hwi']['hw']}",
                            "type": d.get("fl") or f"{d['cxs'][0]['cxl']}",
                            "text": ("- " + "\n- ".join(d["shortdef"]))
                            if d.get("fl")
                            else d["cxs"][0]["cxtis"][0]["cxt"],
                        }
                    )
                    for d in jsonResp
                ]

            return DefinitionResponse(term=term, definitions=definitions)

    except Exception as e:
        pprint(e)
        log.error(e)
        raise HTTPException(500, e)
