import requests

def search_wikipedia(query: str) -> dict:
    """Searches Wikipedia for a given term and returns a brief summary.

    Args:
        query: The search term (e.g., a compound name like 'aspirin' or 'paracetamol').

    Returns:
        A dictionary containing the 'summary' and 'url' of the Wikipedia page.
    """
    query = query.strip()
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
    
    try:
        response = requests.get(url, headers={"User-Agent": "OrganicChemAgent/1.0 (NTU Workshop)"})
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "summary": data.get("extract", "No summary found."),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
            }
        else:
            return {"status": "error", "message": f"Wikipedia page not found (Status Code: {response.status_code})."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
