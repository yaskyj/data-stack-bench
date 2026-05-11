"""Provider-agnostic LLM client built on LiteLLM.

Single entry point: `extract(system, user, schema) -> dict`. Returns parsed
JSON validated against the supplied JSONSchema. Provider chosen via env vars;
defaults documented in `.env.example`.

Why a wrapper at all: the extraction prompt is single-purpose and short-context,
any frontier chat model handles it. The project is cross-cloud and we want
anyone with credentials for *any* supported provider to be able to reproduce
the analysis end-to-end. That's a methodology contract — see methodology.md
"Extraction pass" — not a nice-to-have.

LLM_PROVIDER values:
    anthropic   -> ANTHROPIC_API_KEY
    bedrock     -> AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS_REGION
    openai      -> OPENAI_API_KEY
    vertex      -> GOOGLE_APPLICATION_CREDENTIALS + VERTEX_AI_PROJECT + VERTEX_AI_LOCATION

Any other LiteLLM-supported provider works too — set LLM_PROVIDER=passthrough
and LLM_MODEL to the LiteLLM model string directly. See:
https://docs.litellm.ai/docs/providers

A stub mode is supported for offline plumbing tests:
    LLM_PROVIDER=stub   -> extract() returns a deterministic stub response.
This lets the pipeline run end-to-end on a fresh checkout before any cloud
credentials are wired up.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=False)  # picks up .env if present


# ---- Provider config ----

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    # Cross-region US inference profile — more resilient than a single-region
    # model ID. Both are valid; the profile balances across us-east-1/us-west-2.
    "bedrock": "bedrock/us.anthropic.claude-sonnet-4-6",
    "openai": "gpt-4.1",
    "vertex": "vertex_ai/claude-sonnet-4-6",
    "stub": "stub",
}


@dataclass
class ProviderConfig:
    provider: str
    model: str

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        provider = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()
        model = os.environ.get("LLM_MODEL") or DEFAULT_MODELS.get(provider)
        if not model:
            raise RuntimeError(
                f"LLM_PROVIDER={provider!r} has no default model. "
                "Set LLM_MODEL explicitly."
            )
        return cls(provider=provider, model=model)


# ---- Errors ----

class LLMError(RuntimeError):
    """Wraps any provider error so callers can retry uniformly."""


# ---- Stub mode ----

def _stub_response(system: str, user: str) -> dict:
    """Deterministic stub used when LLM_PROVIDER=stub.

    Returns a minimally-valid extracted-row shape so downstream stages can
    exercise their plumbing. Values are obvious placeholders so accidental
    use of stubbed data in real analysis is easy to spot.
    """
    return {
        "company_name": "STUB_COMPANY",
        "company_size_band": "unknown",
        "company_stage_signal": "unknown",
        "industry": "saas",
        "role_title_raw": "STUB Role",
        "role_title_normalized": "data_engineer",
        "seniority": "senior",
        "geo": "us",
        "stack_mentions_raw": user[:400],
        "stack_components_normalized": [],
        "notes": "STUB extraction — LLM_PROVIDER=stub",
        "keep": True,
        "exclude_reason": "",
        "confidence": "low",
    }


# ---- Public API ----

def extract(
    system: str,
    user: str,
    schema: dict[str, Any] | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1500,
) -> dict:
    """Run a single extraction call. Returns parsed JSON.

    The model is asked to return strict JSON; the response is parsed and
    (optionally) validated against `schema`. Validation errors raise LLMError —
    upstream code can choose to retry, skip, or escalate.
    """
    cfg = ProviderConfig.from_env()

    if cfg.provider == "stub":
        out = _stub_response(system, user)
    else:
        out = _call_litellm(cfg, system, user, temperature, max_tokens)

    if schema is not None:
        try:
            import jsonschema  # type: ignore[import]
            jsonschema.validate(out, schema)
        except jsonschema.ValidationError as e:
            raise LLMError(f"LLM response failed schema validation: {e.message}") from e

    return out


def _call_litellm(
    cfg: ProviderConfig,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
) -> dict:
    import litellm  # type: ignore[import]

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    # response_format=json_object is supported by Anthropic, OpenAI, Bedrock
    # (Anthropic models), and Vertex AI Anthropic. For providers that don't
    # support it, LiteLLM falls back gracefully — the model still returns JSON
    # because the system prompt demands it. We catch JSON decode errors and
    # surface as LLMError.
    kwargs: dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # Anthropic + OpenAI support response_format; Bedrock Anthropic does too via LiteLLM.
    if cfg.provider in ("anthropic", "openai", "bedrock", "vertex"):
        kwargs["response_format"] = {"type": "json_object"}

    try:
        resp = litellm.completion(**kwargs)
    except Exception as e:  # broad: LiteLLM surfaces many provider error types
        raise LLMError(f"LLM call failed via {cfg.provider}: {e}") from e

    try:
        content = resp.choices[0].message.content  # type: ignore[union-attr,index]
    except (AttributeError, IndexError, KeyError) as e:
        raise LLMError(f"Unexpected LLM response shape: {resp!r}") from e

    if not content:
        raise LLMError("LLM returned empty content")

    return _parse_json_from_response(content)


def _parse_json_from_response(content: str) -> dict:
    """Best-effort JSON extraction from LLM output.

    The system prompt asks for strict JSON, but models occasionally preamble
    ("Let me think...") or wrap in ```json fences. We try in order:
      1. Plain json.loads on the stripped content.
      2. Stripping markdown code fences.
      3. Finding the outermost balanced { ... } block and parsing that.
    """
    text = content.strip()

    # Fast path.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Code-fence strip.
    if text.startswith("```"):
        inner = text.split("\n", 1)[1] if "\n" in text else text
        if inner.endswith("```"):
            inner = inner.rsplit("```", 1)[0]
        inner = inner.strip()
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            text = inner  # fall through with the unfenced text

    # Slow path: balanced-brace scan. Handles prose-then-JSON and JSON-then-prose.
    start = text.find("{")
    if start == -1:
        raise LLMError(f"LLM response had no JSON object: {content!r}")
    depth = 0
    in_str = False
    escape = False
    end = -1
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        raise LLMError(f"LLM response had unbalanced JSON: {content!r}")
    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise LLMError(f"LLM response was not valid JSON: {e}; content={content!r}") from e


# ---- CLI smoke test ----

def _smoke() -> int:
    """Quick check: run a trivial extraction and print the parsed result.

    Usage:
        LLM_PROVIDER=stub python llm_client.py
        LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... python llm_client.py
    """
    system = "Return JSON of the form {\"ok\": true, \"echo\": \"<input>\"}. Strict JSON only."
    user = "ping"
    out = extract(system, user)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke())
