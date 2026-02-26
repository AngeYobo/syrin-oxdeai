"""Dependency Injection Example (v0.3.0+).

Demonstrates:
- Passing dependencies to tools via closure (pattern until Agent[Deps] exists)
- Injected services (e.g. search client) used by tools
- Testing with mock dependencies

Run: python -m examples.08_advanced.dependency_injection
"""

from pathlib import Path

from dotenv import load_dotenv

from examples.models.models import almock
from syrin import Agent, tool

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def create_search_tool(search_client):
    """Factory: create tool with injected search_client."""

    @tool
    def search(query: str) -> str:
        return search_client.search(query)

    return search


class MockSearchClient:
    def search(self, query: str) -> str:
        return f"[MOCK] Results for: {query}"


search_client = MockSearchClient()
search_tool = create_search_tool(search_client)
agent = Agent(
    model=almock,
    system_prompt="Use search to find information.",
    tools=[search_tool],
)
result = agent.response("Search for AI trends")
print(f"Result: {result.content[:100]}...")
