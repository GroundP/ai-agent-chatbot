from typing import Type
from crewai.tools import BaseTool
from litellm import integrations
from openai.types.responses import web_search_preview_tool
from pydantic import BaseModel, Field
from env import (
    FIRECRAWL_API_KEY,
    NAVER_API_CLIENT_ID,
    NAVER_API_CLIENT_SECRET,
)
from firecrawl import Firecrawl
import requests
import re


class NaverSearchToolInput(BaseModel):
    """Input schema for NaverSearchTool."""

    query: str = Field(..., description="The search query to look for.")
    display: int = Field(
        default=10, description="Number of search results to display (max 100)."
    )


class NaverSearchTool(BaseTool):
    name: str = "naver_search_tool"
    description: str = (
        "Searches Naver for Korean web content based on a query and returns relevant results with titles, URLs, and descriptions."
    )
    args_schema: Type[BaseModel] = NaverSearchToolInput

    def _run(self, query: str, display: int = 10):
        try:
            url = "https://openapi.naver.com/v1/search/webkr"
            headers = {
                "X-Naver-Client-Id": NAVER_API_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_API_CLIENT_SECRET,
                "Content-Type": "application/json",
            }

            params = {"query": query, "display": min(display, 100)}  # API limit is 100

            print(f"[DEBUG] Making request to Naver API with query: {query}")

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            print(f"[DEBUG] Raw response type: {type(data)}")
            print(f"[DEBUG] Raw response: {data}")

            if "items" not in data or not data["items"]:
                return f"No search results found for query: {query}"

            search_results = []

            for item in data["items"]:
                title = item.get("title", "No Title")
                # Remove HTML tags from title
                title = re.sub(r"<[^>]+>", "", title)

                url = item.get("link", "")
                description = item.get("description", "")
                # Remove HTML tags from description
                description = re.sub(r"<[^>]+>", "", description)

                search_results.append(
                    {
                        "title": title,
                        "url": url,
                        "content": (
                            description[:500] + "..."
                            if len(description) > 500
                            else description
                        ),
                    }
                )

            result = {
                "query": query,
                "results_count": len(search_results),
                "total": data.get("total", 0),
                "results": search_results,
            }

            print("DEBUG : ", result)

            return result

        except Exception as e:
            return f"Error searching for query '{query}': {e}"


def _web_search(query: str):
    firecrawl = Firecrawl(api_key=FIRECRAWL_API_KEY)
    response = firecrawl.search(query, limit=5)
    if not response:
        return f"No results found for query: {query}"

    search_results = []
    if response.web:
        for result in response.web:
            title = getattr(result, "title", "No title")
            url = getattr(result, "url", "")
            description = getattr(result, "description", "")

            search_results.append(
                {
                    "title": title,
                    "url": url,
                    "content": (
                        description[:500] + "..."
                        if len(description) > 500
                        else description
                    ),
                }
            )

            search_result = {
                "query": query,
                "results_count": len(search_results),
                "results": search_results,
            }
    return search_result


class WebSearchToolInput(BaseModel):
    """Input schema for WebSearchTool."""

    query: str = Field(..., description="The search query to look for.")


class WebSearchTool(BaseTool):
    name: str = "web_search_tool"
    description: str = (
        "Search the web for information based on the query and return relevant results with titles, URLs, and content snippets."
    )
    args_schema: Type[BaseModel] = WebSearchToolInput

    def _run(self, query: str):
        return _web_search(query)


# web_search_tool = WebSearchTool()
naver_search_tool = NaverSearchTool()
web_search_tool = WebSearchTool()

# print(web_search_tool._run("브롤스타즈"))
