import requests
import json
try:
    import openai
except ImportError:
    openai = None
try:
    import anthropic as anthropic_sdk
except ImportError:
    anthropic_sdk = None


def call_ai(prompt: str, config: dict) -> str:
    provider = config.get("provider", "ollama")

    if provider == "ollama":
        return call_ollama(prompt, config)
    elif provider == "anthropic":
        return call_anthropic(prompt, config)
    elif provider == "openai":
        return call_openai(prompt, config)
    elif provider == "kimi":
        return call_kimi(prompt, config)
    elif provider == "minimax":
        return call_minimax(prompt, config)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def test_connection(config: dict) -> tuple[bool, str]:
    try:
        response = call_ai("Reply with exactly: OK", config)
        provider = config.get("provider", "ollama")
        model = _get_model_name(config)
        if response:
            return True, f"Connected to {provider} ({model})"
        return False, "Empty response from provider"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def _get_model_name(config: dict) -> str:
    provider = config.get("provider", "ollama")
    if provider == "ollama":
        return config.get("ollama_model", "llama3")
    elif provider == "anthropic":
        return config.get("anthropic_model", "claude-3-5-sonnet-20241022")
    elif provider == "openai":
        return config.get("openai_model", "gpt-4o")
    elif provider == "kimi":
        return config.get("kimi_model", "moonshot-v1-32k")
    elif provider == "minimax":
        return config.get("minimax_model", "abab6.5-chat")
    return "unknown"


def call_ollama(prompt: str, config: dict) -> str:
    base_url = config.get("ollama_url", "http://localhost:11434")
    model = config.get("ollama_model", "llama3")
    url = f"{base_url}/api/generate"

    try:
        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise ValueError(
            "Ollama not running. Install from ollama.ai, then run: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise ValueError("Ollama timed out. Try a smaller model or shorter code.")
    except Exception as e:
        raise ValueError(f"Ollama error: {str(e)}")


def call_anthropic(prompt: str, config: dict) -> str:
    if anthropic_sdk is None:
        raise ValueError("anthropic package not installed. Run: pip install anthropic")

    api_key = config.get("api_key", "")
    if not api_key:
        raise ValueError("Anthropic API key not set. Go to Settings.")

    model = config.get("anthropic_model", "claude-3-5-sonnet-20241022")

    try:
        client = anthropic_sdk.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic_sdk.AuthenticationError:
        raise ValueError("Invalid Anthropic API key. Check Settings.")
    except anthropic_sdk.RateLimitError:
        raise ValueError("Anthropic rate limit hit. Wait a moment and retry.")
    except Exception as e:
        raise ValueError(f"Anthropic error: {str(e)}")


def call_openai(prompt: str, config: dict) -> str:
    if openai is None:
        raise ValueError("openai package not installed. Run: pip install openai")

    api_key = config.get("api_key", "")
    if not api_key:
        raise ValueError("OpenAI API key not set. Go to Settings.")

    model = config.get("openai_model", "gpt-4o")

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.3
        )
        return response.choices[0].message.content
    except openai.AuthenticationError:
        raise ValueError("Invalid OpenAI API key. Check Settings.")
    except openai.RateLimitError:
        raise ValueError("OpenAI rate limit hit. Wait a moment and retry.")
    except Exception as e:
        raise ValueError(f"OpenAI error: {str(e)}")


def call_kimi(prompt: str, config: dict) -> str:
    api_key = config.get("api_key", "")
    if not api_key:
        raise ValueError("Kimi API key not set. Go to Settings.")

    model = config.get("kimi_model", "moonshot-v1-32k")

    try:
        response = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise ValueError("Invalid Kimi API key. Check Settings.")
        raise ValueError(f"Kimi API error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Kimi error: {str(e)}")


def call_minimax(prompt: str, config: dict) -> str:
    api_key = config.get("api_key", "")
    if not api_key:
        raise ValueError("MiniMax API key not set. Go to Settings.")

    model = config.get("minimax_model", "abab6.5-chat")

    try:
        response = requests.post(
            "https://api.minimax.chat/v1/text/chatcompletion_v2",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise ValueError("Invalid MiniMax API key. Check Settings.")
        raise ValueError(f"MiniMax API error: {str(e)}")
    except Exception as e:
        raise ValueError(f"MiniMax error: {str(e)}")


def prompt_security_review(code: str) -> str:
    return f"""You are a senior security engineer reviewing code like a professional security audit.

STRICT RULES:
- Be honest. Be direct. Do not sugarcoat issues.
- Only report REAL security issues. Do not invent problems.
- If the code is secure, say so clearly.

CODE TO REVIEW:
{code}

Find every security vulnerability. For each one, give:

ISSUE: [name of the vulnerability]
SEVERITY: [CRITICAL / HIGH / MEDIUM / LOW]
LINE REFERENCE: [approximate line number or function name]
EXPLANATION: [exactly what the problem is and why it is dangerous]
FIX: [exact code fix or clear instructions to fix it]

After all issues, give:
SECURITY SCORE: [0-100, where 100 = no issues found]
SUMMARY: [one sentence overall assessment]

If no security issues exist, say:
SECURITY SCORE: 100
SUMMARY: No security vulnerabilities found in this code.

Do not add disclaimers, apologies, or filler text. Be surgical."""


def prompt_logic_review(code: str) -> str:
    return f"""You are a senior software engineer doing a logic and correctness review.

STRICT RULES:
- Only flag REAL logic errors. Do not invent problems.
- Focus on: wrong assumptions, off-by-one errors, null/undefined handling,
  race conditions, incorrect boolean logic, missing edge cases.
- If the logic is correct, say so clearly.

CODE TO REVIEW:
{code}

Find every logic error or correctness issue. For each one, give:

ISSUE: [name of the logic problem]
SEVERITY: [HIGH / MEDIUM / LOW]
LINE REFERENCE: [approximate line number or function name]
EXPLANATION: [exactly what is wrong and when it would fail]
FIX: [exact fix or clear instructions]

After all issues, give:
LOGIC SCORE: [0-100]
SUMMARY: [one sentence overall assessment]

If no logic issues exist, say:
LOGIC SCORE: 100
SUMMARY: No logic errors found in this code.

Do not add disclaimers or filler. Be direct."""


def prompt_scalability_review(code: str) -> str:
    return f"""You are a senior backend engineer reviewing code for performance and scalability.

STRICT RULES:
- Only flag REAL scalability problems that matter at scale.
- Focus on: N+1 queries, missing indexes, unbounded loops, memory leaks,
  synchronous blocking calls, missing pagination, inefficient data structures.
- If the code scales fine, say so.

CODE TO REVIEW:
{code}

Find every scalability or performance problem. For each one, give:

ISSUE: [name of the problem]
SEVERITY: [HIGH / MEDIUM / LOW]
LINE REFERENCE: [approximate line number or function name]
EXPLANATION: [what breaks and at what scale]
FIX: [exact fix or clear instructions]

After all issues, give:
SCALE SCORE: [0-100]
SUMMARY: [one sentence overall assessment]

Do not add disclaimers or filler. Be direct."""


def prompt_code_quality_review(code: str) -> str:
    return f"""You are a senior engineer reviewing code quality, maintainability, and best practices.

STRICT RULES:
- Only flag things that genuinely make code harder to maintain or debug.
- Focus on: missing error handling, hardcoded values, dead code, poor naming,
  missing input validation, overly complex functions, missing type hints.
- Skip minor style preferences (tabs vs spaces, etc.).
- If the code quality is good, say so.

CODE TO REVIEW:
{code}

Find every code quality issue. For each one, give:

ISSUE: [name of the problem]
SEVERITY: [HIGH / MEDIUM / LOW]
LINE REFERENCE: [approximate line number or function name]
EXPLANATION: [why this causes problems]
FIX: [exact fix or clear instructions]

After all issues, give:
QUALITY SCORE: [0-100]
SUMMARY: [one sentence overall assessment]

Do not add filler. Be direct."""


def prompt_full_review(code: str) -> str:
    return f"""You are a senior software engineer + security expert doing a full code review.
Act like a tough but fair senior engineer who genuinely wants to help ship better code.

CODE TO REVIEW:
{code}

Do a full audit across 4 dimensions:

== SECURITY ==
Find every security vulnerability.
For each: ISSUE | SEVERITY (CRITICAL/HIGH/MEDIUM/LOW) | LINE | EXPLANATION | FIX

== LOGIC ==
Find every logic error or incorrect assumption.
For each: ISSUE | SEVERITY (HIGH/MEDIUM/LOW) | LINE | EXPLANATION | FIX

== SCALABILITY ==
Find every performance or scalability problem.
For each: ISSUE | SEVERITY (HIGH/MEDIUM/LOW) | LINE | EXPLANATION | FIX

== CODE QUALITY ==
Find every maintainability issue worth fixing.
For each: ISSUE | SEVERITY (HIGH/MEDIUM/LOW) | LINE | EXPLANATION | FIX

== SCORES ==
SECURITY SCORE: [0-100]
LOGIC SCORE: [0-100]
SCALE SCORE: [0-100]
QUALITY SCORE: [0-100]
OVERALL SCORE: [0-100, weighted average]

== VERDICT ==
[2-3 sentences. Is this code safe to ship? What is the #1 thing to fix first?]

RULES:
- Only report REAL issues. Never invent problems.
- If a category has no issues, say "No issues found" and give score 100.
- Be direct. Skip disclaimers and filler text.
- Format must be exactly as above so it can be parsed."""