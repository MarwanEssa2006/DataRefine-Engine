"""
╔══════════════════════════════════════════════════════════════╗
║              AI CONSULTANT  —  Gemini-Powered Brain          ║
║                                                              ║
║  Uses direct REST API calls — no library version issues      ║
║  Tries every available Gemini model automatically            ║
║  Free tier: 1,500 requests/day — no credit card needed       ║
║  Get your key: aistudio.google.com                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import re
import urllib.request
import urllib.error


# ══════════════════════════════════════════════════════════════
# GEMINI REST ENDPOINTS
# Using v1 (stable) not v1beta — broader model availability
# ══════════════════════════════════════════════════════════════

GEMINI_V1_URL    = "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={key}"
GEMINI_LIST_URL  = "https://generativelanguage.googleapis.com/v1/models?key={key}"

# Models to try in order — stops at first success
CANDIDATE_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.0-pro",
    "gemini-pro",
]


# ══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a Senior Data Engineer and Data Quality Consultant with 15+ years of experience.

You will receive a JSON audit report produced by an automated data profiling tool called DataAuditor.
Your job is to:
  1. Read every check in the report carefully.
  2. Prioritize issues by business impact (not just severity label).
  3. Return a precise, machine-readable Cleaning Strategy JSON.

AVAILABLE CLEANING OPERATIONS
These are the ONLY valid keys you may approve in the permissions dict:

  duplicates          - drops exact duplicate rows
  empty_rows          - removes rows that are entirely null/blank
  nulls               - fills nulls: mean/median/mode based on skew
  outliers            - caps outliers via IQR clipping
  column_names        - renames columns to snake_case
  string_quality      - strips whitespace, normalizes casing
  date_formats        - parses date strings to proper datetime
  data_types          - casts numeric strings to float
  sparse_columns      - drops columns that are more than 50% empty
  constant_columns    - drops columns with zero variance
  high_correlation    - drops one column from highly correlated pairs
  email_format        - flags invalid email addresses
  phone_format        - flags invalid phone numbers
  test_data           - flags rows containing junk/test keywords
  typos               - merges near-duplicate categorical values

OUTPUT FORMAT - return ONLY this JSON, nothing else, no markdown fences:

{
  "permissions": {
    "duplicates": true,
    "empty_rows": true,
    "nulls": true,
    "outliers": false,
    "column_names": true,
    "string_quality": true,
    "date_formats": false,
    "data_types": true,
    "sparse_columns": false,
    "constant_columns": false,
    "high_correlation": false,
    "email_format": false,
    "phone_format": false,
    "test_data": false,
    "typos": false
  },
  "rationale": {
    "duplicates": "one sentence explaining your decision",
    "empty_rows": "one sentence explaining your decision",
    "nulls": "one sentence explaining your decision",
    "outliers": "one sentence explaining your decision",
    "column_names": "one sentence explaining your decision",
    "string_quality": "one sentence explaining your decision",
    "date_formats": "one sentence explaining your decision",
    "data_types": "one sentence explaining your decision",
    "sparse_columns": "one sentence explaining your decision",
    "constant_columns": "one sentence explaining your decision",
    "high_correlation": "one sentence explaining your decision",
    "email_format": "one sentence explaining your decision",
    "phone_format": "one sentence explaining your decision",
    "test_data": "one sentence explaining your decision",
    "typos": "one sentence explaining your decision"
  },
  "executive_summary": "2-3 sentence plain-English summary of the dataset health and top priorities.",
  "risk_flags": ["Any high-risk observations beyond the standard checks."],
  "confidence": "HIGH or MEDIUM or LOW"
}

RULES:
- Only set a permission to true if that check was found=true in the audit report.
- Never approve a fix for a check that was not found (found=false).
- Be conservative with outliers and high_correlation unless severity is HIGH.
- If PII columns are detected, always mention them in risk_flags.
- Return ONLY the JSON object. No markdown, no preamble, no explanation outside the JSON.
"""


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _compress_report(report: dict) -> dict:
    """Return a lean version of the audit report to save tokens."""
    compressed = {
        "shape":        report.get("shape", {}),
        "health_score": report.get("health_score"),
        "health_grade": report.get("health_grade"),
        "issues_found": report.get("issues_found"),
        "checks":       {},
    }
    for key, check in report.get("checks", {}).items():
        slim = {
            "label":    check.get("label"),
            "found":    check.get("found"),
            "severity": check.get("severity"),
            "category": check.get("category"),
        }
        for field in ("count", "total", "pct", "total_bad", "columns"):
            if field in check:
                slim[field] = check[field]
        if "pairs" in check:
            slim["pairs"] = check["pairs"][:5]
        if key == "nulls" and "by_column" in check:
            slim["worst_null_columns"] = dict(
                sorted(check["by_column"].items(),
                       key=lambda x: x[1].get("pct", 0), reverse=True)[:5]
            )
        if key in ("string_quality", "mixed_types", "typos") and "by_column" in check:
            slim["affected_columns_count"] = len(check["by_column"])
        compressed["checks"][key] = slim
    return compressed


def _default_permissions(report: dict) -> dict:
    """Safe fallback: approve only HIGH-severity found checks."""
    checks = report.get("checks", {})
    return {
        key: bool(check.get("found") and check.get("severity") == "HIGH")
        for key, check in checks.items()
        if key not in ("pii", "mixed_types", "schema_issues")
    }


def _parse_response(raw_text: str) -> dict:
    """
    Extract JSON from the model response.

    Strips markdown code fences only at the very start and end of the
    response — not on every line — to avoid corrupting JSON values that
    happen to start with triple-backticks.
    """
    text = raw_text.strip()
    # Remove a single leading fence (```json or ```) if present
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    # Remove a single trailing fence if present
    text = re.sub(r"\n?\s*```\s*$", "", text)
    text = text.strip()
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response.")
    return json.loads(text[start:end])


def _call_gemini(model_name: str, prompt: str, api_key: str) -> str:
    """
    Direct REST call to Gemini v1 API.
    Returns the response text or raises an exception.
    No external library needed — uses only Python stdlib urllib.
    """
    url     = GEMINI_V1_URL.format(model=model_name, key=api_key)
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature":    0.1,
            "maxOutputTokens": 4096,
        }
    }
    data    = json.dumps(payload).encode("utf-8")
    req     = urllib.request.Request(
        url,
        data    = data,
        headers = {"Content-Type": "application/json"},
        method  = "POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    # Extract text from response
    return result["candidates"][0]["content"]["parts"][0]["text"]


def _list_available_models(api_key: str) -> list:
    """
    Fetch the list of models available for this API key.
    Returns model names that support generateContent.
    """
    url = GEMINI_LIST_URL.format(key=api_key)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        models = []
        for m in result.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                # name is like "models/gemini-1.5-flash" — strip the prefix
                name = m["name"].replace("models/", "")
                models.append(name)
        return models
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════════

def get_ai_strategy(audit_report: dict, api_key: str) -> dict:
    """
    Send the audit report to Gemini and return a cleaning strategy.

    Returns a dict with keys:
        permissions       — {check_key: bool}  ready for DataCleaner.run()
        rationale         — {check_key: str}   one sentence per check
        executive_summary — str
        risk_flags        — list[str]
        confidence        — "HIGH" | "MEDIUM" | "LOW"
        error             — str | None
    """
    # ── Build the full prompt ──────────────────────────────────
    compressed  = _compress_report(audit_report)
    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "Here is the DataAuditor report:\n\n"
        f"{json.dumps(compressed, indent=2, default=str)}\n\n"
        "Return your Cleaning Strategy JSON now."
    )

    # ── Try each candidate model until one works ───────────────
    # First: try to get the real list of available models for this key
    available = _list_available_models(api_key)

    # Build try-order: real available models first, then our hardcoded list
    # Filter to only flash/pro models (skip embedding, vision-only, etc.)
    flash_pro = [m for m in available if any(k in m for k in ("flash", "pro", "gemini"))]
    try_order = flash_pro + [m for m in CANDIDATE_MODELS if m not in flash_pro]

    # Deduplicate while preserving order
    seen      = set()
    try_order = [m for m in try_order if not (m in seen or seen.add(m))]

    raw_text   = None
    used_model = None
    errors     = []

    for model_name in try_order:
        try:
            raw_text   = _call_gemini(model_name, full_prompt, api_key)
            used_model = model_name
            break
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            err_info = f"{model_name}: HTTP {e.code} — {body[:200]}"
            errors.append(err_info)

            # Stop immediately on auth errors — no point trying other models
            if e.code in (400, 403):
                body_lower = body.lower()
                if "api_key_invalid" in body_lower or "api key not valid" in body_lower:
                    return {
                        "permissions":       _default_permissions(audit_report),
                        "rationale":         {},
                        "executive_summary": "",
                        "risk_flags":        [],
                        "confidence":        "LOW",
                        "error": "Invalid API key. Get a free key at aistudio.google.com",
                    }
            continue
        except Exception as e:
            errors.append(f"{model_name}: {str(e)[:150]}")
            continue

    # ── All models failed ──────────────────────────────────────
    if raw_text is None:
        errors_str = " | ".join(errors[:3])
        return {
            "permissions":       _default_permissions(audit_report),
            "rationale":         {},
            "executive_summary": "",
            "risk_flags":        [],
            "confidence":        "LOW",
            "error": (
                f"All Gemini models failed. Tried: {', '.join(try_order[:5])}. "
                f"Errors: {errors_str}"
            ),
        }

    # ── Parse response ─────────────────────────────────────────
    try:
        parsed = _parse_response(raw_text)
    except Exception as e:
        return {
            "permissions":       _default_permissions(audit_report),
            "rationale":         {},
            "executive_summary": "",
            "risk_flags":        [],
            "confidence":        "LOW",
            "error": f"Could not parse response from {used_model}: {str(e)}. Raw: {raw_text[:300]}",
        }

    # ── Sanitize permissions ───────────────────────────────────
    valid_keys  = set(audit_report.get("checks", {}).keys()) - {"pii", "mixed_types"}
    raw_perms   = parsed.get("permissions", {})
    clean_perms = {k: bool(v) for k, v in raw_perms.items() if k in valid_keys}
    for k in valid_keys:
        clean_perms.setdefault(k, False)

    return {
        "permissions":       clean_perms,
        "rationale":         parsed.get("rationale", {}),
        "executive_summary": parsed.get("executive_summary", ""),
        "risk_flags":        parsed.get("risk_flags", []),
        "confidence":        parsed.get("confidence", "MEDIUM"),
        "error":             None,
    }