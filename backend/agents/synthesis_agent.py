from config.settings import (
    get_llm_response,
    GROQ_MAIN_MODEL
)


class SynthesisAgent:

    def synthesize(
        self,
        user_query,
        agent_outputs,
        session_context=None
    ):

        combined = "\n\n".join([

            f"{k}:\n{v}"

            for k, v in agent_outputs.items()
        ])

        # Build session context summary for continuity
        session_summary = ""
        if session_context:
            dialogue_frame = session_context.get("dialogue_frame", {})
            slots = dialogue_frame.get("slots", {})
            slot_history = session_context.get("session_state", {}).get("slot_history", {})
            active_topic = dialogue_frame.get("active_topic")
            pending_question = dialogue_frame.get("pending_question", {}).get("question")
            
            if slots or slot_history or active_topic or pending_question:
                session_summary = "Session history so far:\n"
                if active_topic:
                    session_summary += f"- Active topic: {active_topic}\n"
                if slots:
                    filled_slots = [f"{k}: {v}" for k, v in slots.items() if v]
                    if filled_slots:
                        session_summary += f"- User reported: {', '.join(filled_slots)}\n"
                if pending_question:
                    session_summary += f"- Pending question: {pending_question}\n"
                if slot_history:
                    asked_slots = [k for k, v in slot_history.items() if v.get("asked_at_turn")]
                    if asked_slots:
                        session_summary += f"- Already explored: {', '.join(asked_slots)}\n"

        messages = [

            {
                "role": "system",
                "content": (
                    "You are a calm, supportive medical assistant.\n\n"
                    "Output must follow this structure exactly:\n\n"
                    "1) A short acknowledgement sentence.\n"
                    "2) A simple explanation (1-2 lines).\n"
                    "3) Practical guidance as short bullet • points.\n"
                    "4) Red flags / safety advice if relevant (short).\n"
                    "5) One concise follow-up question only.\n\n"
                    "Style and rules:\n"
                    "- Use short natural paragraphs and bullet • lists.\n"
                    "- Use bullet • lists for practical guidance, comfort measures, or red-flag warnings whenever possible.\n"
                    "- Avoid medical jargon and long disclaimers.\n"
                    "- Never ask multiple questions; only one follow-up question.\n"
                    "- Keep overall response ideally between 80-180 words unless more detail is needed.\n"
                    "- Tone: calm, empathetic, conversational, non-robotic.\n"
                    "- Do NOT repeat the user's symptom phrases excessively.\n"
                    "- Reference previous symptoms from session if mentioned earlier (for example, 'You mentioned fever and headache before').\n"
                    "- Use session context to avoid re-asking about previously provided details.\n"
                    "- If the latest user message answers a pending question, continue assessment without restarting the flow.\n"
                    "- Do not include any numbered sections or headings aside from the bullet • list requested.\n"
                    "- Return plain text formatted with markdown paragraphs and bullet  •  points.\n\n"
                    "When given agent outputs, combine them concisely into the required structure and ensure the final text reads like one assistant reply."
                )
            },

            {
                "role": "user",
                "content": (
                    f"{session_summary}\n"
                    f"User's Latest Message:\n{user_query}\n\n"
                    f"Agent Outputs (combine and synthesize):\n{combined}"
                )
            }
        ]

        return get_llm_response(

            messages,

            model=GROQ_MAIN_MODEL,

            temperature=0.25,

            max_tokens=480
        )