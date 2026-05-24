from tools.symptom_tool import analyze_symptoms

from tools.health_record_tool import (
    fetch_health_history
)

from config.logger import logger


class SymptomAgent:
    """
    Responsible for:
    - Conversational symptom analysis
    - Medical reasoning
    - Context-aware health responses
    - Long-term memory integration
    """

    def __init__(self):

        self.name = "SymptomAgent"

    def analyze(
        self,
        symptoms_english: str,
        phone_number: str,
        user_name: str,
        age: int,
        gender: str,
        conversation_history: list = None,
        medical_context: str = "",
        summary_memory: str = "",
        vector_context: str = "",
        structured_profile: str = "",
        long_term_memory: str = "",
        conversation_state: dict = None,
        session_context: dict = None
    ) -> dict:
        """
        Analyze symptoms conversationally
        using:
        - recent conversation memory
        - summarized memory
        - vector memory retrieval
        - structured medical profile
        """

        # ─────────────────────────────────────
        # Fetch past health history
        # ─────────────────────────────────────

        history_data = fetch_health_history(

            phone_number,

            limit=3
        )

        past_records = history_data.get(

            "records",

            []
        )

        logger.info(

            f"[{self.name}] "
            f"Analyzing symptoms: "
            f"{symptoms_english[:60]}"
        )

        # ─────────────────────────────────────
        # Main AI Analysis
        # ─────────────────────────────────────

        result = analyze_symptoms(

            symptoms=symptoms_english,

            user_name=user_name,

            age=age,

            gender=gender,

            past_history=past_records,

            conversation_history=conversation_history,

            medical_context=medical_context,

            summary_memory=summary_memory,

            vector_context=vector_context,

            structured_profile=structured_profile,

            long_term_memory=long_term_memory,

            conversation_state=conversation_state,
            session_context=session_context
        )

        # ─────────────────────────────────────
        # Return response
        # ─────────────────────────────────────

        return {

            "response":
                result["response"],

            "possible_disease":
                result["possible_disease"],

            "severity":
                result["severity"],

            "see_doctor":
                result["see_doctor"],

            "emergency":
                result["emergency"]
        }

        