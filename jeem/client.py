from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from jeem.models import SSEEvent, TextDelta, TextEnd, DataFollowups, DataSummary, Finish

API_URL = "https://jeem.ai/ext/api/chat"

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://jeem.ai/",
}


async def stream_chat(request_json: dict) -> AsyncIterator[SSEEvent]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(120)) as client:
        async with client.stream(
            "POST", API_URL, headers=HEADERS, json=request_json
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue

                # SSE: "data: {...}" or "event: message\ndata: {...}"
                if line.startswith("data: "):
                    payload = line[len("data: "):]
                else:
                    payload = line

                if payload == "[DONE]":
                    return

                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                event_type = data.get("type")
                if event_type == "text-delta":
                    yield TextDelta(**data)
                elif event_type == "text-end":
                    yield TextEnd(**data)
                elif event_type == "data-followups":
                    yield DataFollowups(**data)
                elif event_type == "data-summary":
                    yield DataSummary(**data)
                elif event_type == "finish":
                    yield Finish(**data)
