import json

from config.settings import (
    get_llm_response,
    GROQ_MAIN_MODEL
)
from config.logger import logger

REASONING_PROMPT = """
You are a medical reasoning evaluator.

Your job:
- Analyze the AI symptom response
- Decide if more information is needed
- Detect uncertainty
- Suggest follow-up questions

Return ONLY JSON.

Format:

{
  "needs_followup": true,
  "followup_question": "question here",
  "reason": "why followup is needed"
}
"""


class ReasoningAgent:

    def __init__(self):
        self.name = "ReasoningAgent"

    def analyze_response(
        self,
        user_input: str,
        symptom_result: dict
    ) -> dict:

        messages = [
            {
                "role": "system",
                "content": REASONING_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"User Symptoms:\n{user_input}\n\n"
                    f"AI Response:\n{json.dumps(symptom_result)}"
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

            return json.loads(cleaned)

        except Exception:

            return {
                "needs_followup": False,
                "followup_question": "",
                "reason": "parse_failed"
            }