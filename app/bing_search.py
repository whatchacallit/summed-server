from app.api_models import SearchResponse
import os, requests, urllib.parse

#
# Get the endpoints, API keys etc from the env
#
subscription_key = os.getenv("BING_CUSTOM_SEARCH_API_KEY")
custom_config_key = os.getenv("BING_CUSTOM_SEARCH_CONFIG_ID")
search_url = os.getenv(
    "BING_CUSTOM_SEARCH_API_BASE_URL", "https://api.bing.microsoft.com/v7.0/custom"
)
page_search_url = f"{search_url}/search"
image_search_url = f"{search_url}/images/search"
video_search_url = f"{search_url}/videos/search"

assert subscription_key


def bing_search_hosted_ui(q: str, language="en"):
    """
    Constructs and returns the Bing Custom Search Hosted UI URL, based on the query string
    """
    market = "en-US"
    queryString = urllib.parse.quote(q.strip())
    url = f"https://ui.customsearch.ai/hosted-page?customconfig={custom_config_key}?version=latest&market={market}&q={queryString}"

    return url


# https://ui.customsearch.ai/hosted-page?customconfig=48d85588-61c9-486c-ac87-9269ce23c5c5&version=latest&market=en-US&q=


def bing_search(q: str) -> SearchResponse:
    """
    Searches for related (web) pages, images and videos for a query expression.
    Used Bing Custom search with a selected domain for (trusted) health information webpages.


    - **q** The search query, e.g. 'breast cancer commonly present lump feel different rest breast tissue'
    """

    search_term = q

    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
    }

    # see: https://docs.microsoft.com/en-us/bing/search-apis/bing-web-search/reference/query-parameters
    page_params = {
        "q": search_term,
        "customconfig": custom_config_key,
        "count": 3,
        "safeSearch": "Off",
        "textDecorations": False,
        "textFormat": "raw",
    }
    image_params = {
        "q": search_term,
        "customconfig": custom_config_key,
        "count": 3,
        "safeSearch": "Off",
    }
    video_params = {
        "q": search_term,
        "customconfig": custom_config_key,
        "count": 3,
        "safeSearch": "Off",
    }

    # Query for "webpages"
    response = requests.get(page_search_url, headers=headers, params=page_params)
    response.raise_for_status()
    pages_results = dict(response.json())

    # Query for "images"
    response = requests.get(image_search_url, headers=headers, params=image_params)
    response.raise_for_status()
    image_results = dict(response.json())

    # Query for "videos"
    response = requests.get(video_search_url, headers=headers, params=video_params)
    response.raise_for_status()
    video_results = dict(response.json())

    # pages_results['webPages']['value'] => (name, url, displayUrl, language, snippet)
    pages = [
        {
            "title": d["name"],
            "url": d["url"],
            "text": d["snippet"],
        }
        for d in pages_results["webPages"]["value"]
    ]
    # pprint(image_results)
    images = [
        {
            "text": d["name"],
            "url": d["contentUrl"],
            "hostPageUrl": d["hostPageUrl"],
            "thumbnailUrl": d["thumbnailUrl"],
            "webSearchUrl": d["webSearchUrl"],
        }
        for d in image_results["value"]
    ]

    # pprint(video_results)
    videos = [
        {
            "text": d["name"],
            "url": d["contentUrl"],
            "hostPageUrl": d["hostPageUrl"],
            "thumbnailUrl": d["thumbnailUrl"],
            "webSearchUrl": d["webSearchUrl"],
        }
        for d in video_results["value"]
    ]

    response = SearchResponse(pages=pages, images=images, videos=videos)

    return response
