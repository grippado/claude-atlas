"""Optional LLM-as-judge pass to refine semantic-duplicate pairs.

This module imports the Anthropic SDK lazily so the package works fine
without the ``semantic`` extra installed.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from claude_atlas.models import Artifact, Edge, EdgeKind

if TYPE_CHECKING:
    pass

DEFAULT_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """You are a senior engineer auditing a user's Claude Code setup.
You will be given two artifacts (agents, skills, or slash commands) that a heuristic
flagged as possibly duplicated. Decide whether they are truly redundant.

Reply with a single JSON object and nothing else:
{
  "verdict": "duplicate" | "overlap" | "distinct",
  "confidence": 0.0 to 1.0,
  "reason": "one short sentence"
}

- "duplicate": same purpose, one should be deleted or merged.
- "overlap": related but serve distinct cases; worth documenting, not deleting.
- "distinct": the heuristic was wrong; they are meaningfully different.
"""


def _format_artifact(a: Artifact) -> str:
    body = (a.body or "")[:1500]
    return (
        f"--- {a.kind.value.upper()}: {a.name} (scope={a.scope.value}) ---\n"
        f"path: {a.path}\n"
        f"description: {a.description}\n"
        f"triggers: {', '.join(a.triggers) if a.triggers else '(none)'}\n"
        f"body (truncated):\n{body}\n"
    )


def _judge_pair(client, a: Artifact, b: Artifact, model: str) -> dict | None:
    user_msg = (
        "Artifact A:\n"
        + _format_artifact(a)
        + "\nArtifact B:\n"
        + _format_artifact(b)
        + "\nReturn the JSON verdict only."
    )
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=300,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(getattr(block, "text", "") for block in resp.content).strip()
        # Strip code fences if the model wrapped the JSON.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
    except Exception:
        return None


def refine_with_llm(
    edges: list[Edge],
    artifacts: list[Artifact],
    model: str = DEFAULT_MODEL,
    max_pairs: int = 50,
) -> list[Edge]:
    """
    Re-examine DUPLICATE_SEMANTIC edges with the LLM. Returns a NEW edge list
    where each refined edge has its ``detail`` annotated with the verdict,
    and edges the LLM judges "distinct" are dropped.

    Requires ANTHROPIC_API_KEY in the environment and the ``anthropic`` package.
    If either is missing, the original edge list is returned unchanged.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return edges
    try:
        from anthropic import Anthropic  # type: ignore
    except ImportError:
        return edges

    client = Anthropic()
    by_id = {a.id: a for a in artifacts}

    refined: list[Edge] = []
    judged_count = 0

    for e in edges:
        if e.kind != EdgeKind.DUPLICATE_SEMANTIC:
            refined.append(e)
            continue
        if judged_count >= max_pairs:
            refined.append(e)
            continue

        a = by_id.get(e.source)
        b = by_id.get(e.target)
        if a is None or b is None:
            refined.append(e)
            continue

        verdict = _judge_pair(client, a, b, model)
        judged_count += 1

        if verdict is None:
            refined.append(e)
            continue

        v = str(verdict.get("verdict", "")).lower()
        conf = float(verdict.get("confidence", 0.0) or 0.0)
        reason = str(verdict.get("reason", "")).strip()

        if v == "distinct":
            # LLM says this isn't actually a duplicate — drop the edge.
            continue

        refined.append(
            Edge(
                source=e.source,
                target=e.target,
                kind=e.kind,
                weight=max(e.weight, conf),
                detail=f"{e.detail} | LLM: {v} ({conf:.2f}) — {reason}",
            )
        )

    return refined
