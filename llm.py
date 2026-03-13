# llm.py
# Multi-provider LLM calls for AI Insights tab
# Supports OpenAI (GPT-4o), Google Gemini, Anthropic Claude

from typing import Literal

DEPTH_PROMPTS = {
    "Summary bullets": """
You are a personal finance analyst reviewing a year or more of credit card statements.
Based on the data provided, give a concise bullet-point analysis covering:

• 3-5 standout spending patterns or anomalies
• Any suspicious or duplicate-looking charges
• Quick wins — subscriptions or recurring charges the user could cancel
• One overall financial habit observation

Keep it brief and scannable. Use plain language, no jargon.
""",
    "Deep narrative analysis": """
You are an expert personal finance analyst reviewing a year or more of credit card statements.
Based on the data provided, write a thorough narrative analysis covering:

1. **Spending Personality** — What do these statements reveal about this person's lifestyle and habits?
2. **Anomalies & Red Flags** — Any duplicate charges, unusual timing, or charges that don't fit the pattern?
3. **Subscription Audit** — Evaluate all recurring and subscription charges. Which ones seem worth it? Which seem forgotten or wasteful?
4. **Year-over-Year Trends** — What's growing? What's declining? Is spending trending in a healthy or concerning direction?
5. **Category Analysis** — Where is the bulk of money going? Is it balanced?
6. **Missed Savings Opportunities** — Specific charges where better options likely exist (e.g. switching providers, bundling services)
7. **Action Items** — A prioritized list of 5 concrete things this person should do after reading this analysis

Be specific, reference actual merchants and amounts from the data. Write for a smart adult who wants honest, direct insight.
""",
}


def build_prompt(data_summary: str, depth: str) -> str:
    system_section = DEPTH_PROMPTS.get(depth, DEPTH_PROMPTS["Summary bullets"])
    return f"""{system_section}

Here is the spending data to analyze:

{data_summary}
"""


def call_openai(prompt: str, api_key: str) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert personal finance analyst. Be direct, specific, and helpful.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.4,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ OpenAI error: {str(e)}"


def call_gemini(prompt: str, api_key: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Gemini error: {str(e)}"


def call_anthropic(prompt: str, api_key: str) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system="You are an expert personal finance analyst. Be direct, specific, and helpful.",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        return f"❌ Anthropic error: {str(e)}"


def get_ai_insights(
    data_summary: str,
    provider: str,
    api_key: str,
    depth: str = "Summary bullets",
) -> str:
    prompt = build_prompt(data_summary, depth)
    if provider == "OpenAI (GPT-4o)":
        return call_openai(prompt, api_key)
    elif provider == "Google Gemini":
        return call_gemini(prompt, api_key)
    elif provider == "Anthropic Claude":
        return call_anthropic(prompt, api_key)
    return "Unknown provider selected."
