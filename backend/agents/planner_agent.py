import json

from config.settings import (
    get_llm_response,
    GROQ_MAIN_MODEL
)

from tools.tool_registry import TOOL_REGISTRY
from config.logger import logger


PLANNER_SYSTEM_PROMPT = """
You are an AI planner for a healthcare multi-agent system.

Your job:
- Analyze the user's request
- Decide which tools should be used
- Return ONLY valid JSON

Users may speak:
- Bengali
- Hindi
- Hinglish
- Banglish
- mixed regional languages
Understand the semantic meaning even if grammar is imperfect.

Available tools:
- symptom_analysis
- health_history
- disease_education
- outbreak_check
- vaccination_rag

Rules:
- symptom questions → symptom_analysis

- education questions → disease_education
- area disease concerns → outbreak_check
- repeated symptoms or history references → health_history
Use vaccination_rag for:
- vaccination questions
- pregnancy care
- maternal health
- infant vaccines
- immunization schedules

Return ONLY JSON in this format:

{
  "plan": [
    {
      "tool": "tool_name",
      "reason": "why this tool is needed"
    }
  ]
}
"""


class PlannerAgent:

    def __init__(self):
        self.name = "PlannerAgent"

    def create_plan(
        self,
        original_input: str,
        english_input: str,
        history: list = None,
        conversation_state: dict = None,
        long_term_memory: str = ""
    ):

        history_text = ""
        if history:
            history_text = "\n".join(
                f"{m['role']}: {m['content']}"
                for m in history[-4:]
            )

        state_text = "None"
        if conversation_state:
            state_text = json.dumps(conversation_state, indent=2, ensure_ascii=False)

        messages = [
            {
                "role": "system",
                "content": PLANNER_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"Conversation:\n{history_text}\n\n"
                    f"Translated English Input:\n{english_input}\n\n"
                    f"Current dialogue state:\n{state_text}\n\n"
                    f"Long-term medical memory:\n{long_term_memory}\n\n"
                    f"Original user input:\n{original_input}"
                )
            }
        ]

        raw = get_llm_response(
            messages,
            model=GROQ_MAIN_MODEL,
            temperature=0.2,
            max_tokens=300
        )

        try:
            cleaned = raw.replace("```json", "").replace("```", "").strip()

            parsed = json.loads(cleaned)

            return parsed.get("plan", [])

        except Exception as e:
            logger.info(f"[PlannerAgent] Failed: {e}")

            return [
                {
                    "tool": "symptom_analysis",
                    "reason": "fallback symptom analysis"
                }
            ]