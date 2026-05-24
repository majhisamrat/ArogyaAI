import json

from config.settings import (
    get_llm_response,
    GROQ_MAIN_MODEL
)


class ConversationStateAgent:

    def update_state(
        self,
        current_message,
        conversation_history,
        previous_state=None,
        last_assistant_message="",
        session_memory=None,
        long_term_memory="",
        session_context=None
    ):

        if previous_state is None:
            previous_state = {}

        recent_history = "\n".join([
            f"{m['role']}: {m['content']}"
            for m in conversation_history[-8:]
        ])

        session_memory_text = "\n".join([
            f"{m['role']}: {m['content']}"
            for m in (session_memory or [])[-10:]
        ])

        # Extract slot history to prevent re-asking
        slot_history_text = ""
        if session_context and "session_state" in session_context:
            slot_history = session_context["session_state"].get("slot_history", {})
            if slot_history:
                slot_history_text = "Slots already asked this session:\n"
                for slot_name, info in slot_history.items():
                    answered_str = "✓ answered" if info.get("answered") else "✗ not answered"
                    slot_history_text += f"- {slot_name}: {answered_str} (turn {info.get('asked_at_turn')})\n"

        previous_state_json = json.dumps(
            previous_state,
            indent=2,
            ensure_ascii=False
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a medical dialogue state tracker for an AI healthcare assistant.\n\n"
                    "Your job is to update the session dialogue frame and determine whether the latest user message continues the existing medical assessment.\n"
                    "Do not restart the consultation when the user is answering the previous assistant question.\n"
                    "Do not ask the same follow-up question again if the relevant slot has already been filled.\n"
                    "Use the current user message and the conversation history to infer which details are already present, especially body location, onset, duration, severity, and symptom quality.\n"
                    "If the user has already given a detail such as left hand pain, do not ask for that again.\n"
                    "Check the 'Slots already asked this session' section - NEVER re-ask these slots in the same conversation.\n"
                    "Return ONLY valid JSON.\n\n"
                    "Output keys:\n"
                    "active_topic, task, stage, state, continue_context, is_answer_to_question, last_assistant_question, pending_question, slots, pending_slots, next_action, note.\n\n"
                    "Use the following values exactly where possible:\n"
                    "state: NEW_TOPIC | FOLLOW_UP | ANSWER_TO_QUESTION | CLARIFICATION | CONTINUE\n"
                    "next_action: continue_assessment | ask_followup | provide_advice | new_topic | clarify\n"
                    "pending_question.slot should be the semantic slot that the user is being asked to fill.\n"
                    "slots should include any extracted medical details.\n"
                    "Note should be a short summary of how this user turn should be handled.\n"
                    "Return valid JSON only."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Conversation history:\n{recent_history}\n\n"
                    f"Previous dialogue state:\n{previous_state_json}\n\n"
                    f"Last assistant message:\n{last_assistant_message}\n\n"
                    f"{slot_history_text}\n\n"
                    f"Recent session memory:\n{session_memory_text}\n\n"
                    f"Long-term medical memory:\n{long_term_memory}\n\n"
                    f"Latest user message:\n{current_message}"
                )
            }
        ]

        response = get_llm_response(
            messages,
            model=GROQ_MAIN_MODEL,
            temperature=0.1,
            max_tokens=280
        )

        try:
            parsed = json.loads(response)
            return self._normalize_state(parsed, previous_state)
        except Exception:
            return self._build_fallback_state(
                previous_state,
                last_assistant_message
            )

    def _normalize_state(self, parsed_state, previous_state):
        normalized = {
            "active_topic": parsed_state.get("active_topic") or previous_state.get("active_topic", ""),
            "task": parsed_state.get("task") or previous_state.get("task", "symptom_assessment"),
            "stage": parsed_state.get("stage") or previous_state.get("stage", "detail_collection"),
            "state": parsed_state.get("state", previous_state.get("state", "FOLLOW_UP")),
            "continue_context": parsed_state.get("continue_context", True),
            "is_answer_to_question": parsed_state.get("is_answer_to_question", False),
            "last_assistant_question": parsed_state.get(
                "last_assistant_question",
                previous_state.get("last_assistant_question", "")
            ),
            "pending_question": parsed_state.get(
                "pending_question",
                previous_state.get("pending_question", {"id": "", "slot": "", "question": ""})
            ),
            "slots": {**previous_state.get("slots", {}), **parsed_state.get("slots", {})},
            "pending_slots": parsed_state.get(
                "pending_slots",
                previous_state.get("pending_slots", [])
            ),
            "next_action": parsed_state.get(
                "next_action",
                previous_state.get("next_action", "continue_assessment")
            ),
            "note": parsed_state.get("note", "")
        }

        if not normalized["pending_question"]:
            normalized["pending_question"] = {
                "id": "",
                "slot": "",
                "question": ""
            }

        return normalized

    def _build_fallback_state(self, previous_state, last_assistant_message):
        return {
            "active_topic": previous_state.get("active_topic", ""),
            "task": previous_state.get("task", "symptom_assessment"),
            "stage": previous_state.get("stage", "detail_collection"),
            "state": previous_state.get("state", "FOLLOW_UP"),
            "continue_context": True,
            "is_answer_to_question": False,
            "last_assistant_question": last_assistant_message or previous_state.get("last_assistant_question", ""),
            "pending_question": previous_state.get("pending_question", {"id": "", "slot": "", "question": ""}),
            "slots": previous_state.get("slots", {}),
            "pending_slots": previous_state.get("pending_slots", []),
            "next_action": previous_state.get("next_action", "continue_assessment"),
            "note": "fallback state due to parse failure"
        }
