import json

from config.settings import (
    get_llm_response,
    GROQ_MAIN_MODEL,
    TEMP_SYMPTOM,
    MAX_TOKENS_SYMPTOM
)

from data.emergency_rules import EMERGENCY_KEYWORDS

from config.logger import logger


SYSTEM_PROMPT = """
You are an empathetic AI healthcare assistant.

Your job is to behave like ChatGPT during healthcare conversations.

CRITICAL LANGUAGE RULE:
- ALWAYS respond in ENGLISH regardless of the language in which the user typed.
- NEVER respond in Hindi, Bengali, Tamil, or any other language.
- The response will be translated to the user's preferred language by a separate translation step.
- Even if prior conversation history contains Hindi or other language messages, respond ONLY in English.

IMPORTANT RULES:
- Speak naturally and conversationally.
- Use conversation state and pending follow-up questions.
- If this user response answers the previous assistant question, continue the same medical assessment without restarting.
- Do not ask the same question again if the relevant slot has already been filled.
- Use the user-provided medical context and the current dialogue frame to continue the consultation.
- Keep responses supportive but concise.
- When appropriate, mention dangerous signs only if they are present.
- If additional details are required, ask one clear follow-up question.

GOOD STYLE:
"I understand your wrist pain. Since it is stabbing and has lasted 2 days, it could be related to tendon irritation or overuse. Does the pain get worse with movement?"

BAD STYLE:
"Possible Disease: Tendonitis"
"""

def build_session_context_summary(session_context: dict) -> str:
    if not session_context:
        return ""

    dialogue_frame = session_context.get("dialogue_frame", {})
    slots = dialogue_frame.get("slots", {})
    pending_question = dialogue_frame.get("pending_question", {})
    slot_history = session_context.get("session_state", {}).get("slot_history", {})

    lines = []
    if slots:
        filled_slots = [f"{k}: {v}" for k, v in slots.items() if v]
        if filled_slots:
            lines.append("- Reported so far: " + ", ".join(filled_slots))

    if pending_question and pending_question.get("slot"):
        lines.append(f"- Pending question: {pending_question.get('question')}")

    if slot_history:
        asked = [k for k, v in slot_history.items() if v.get("asked_at_turn")]
        if asked:
            lines.append("- Already explored: " + ", ".join(asked))

    return "Session Context Summary:\n" + "\n".join(lines) if lines else ""


def analyze_symptoms(
    symptoms: str,
    user_name: str,
    age: int,
    gender: str,
    past_history: list = None,
    conversation_history: list = None,
    medical_context: str = "",
    summary_memory: str = "",
    vector_context: str = "",
    structured_profile: str = "",
    long_term_memory: str = "",
    conversation_state: dict = None,
    session_context: dict = None
) -> dict:

    # Emergency detection first

    emergency = detect_emergency(symptoms)

    if emergency:

        return {

            "response": (
                "⚠️ Your symptoms may require urgent medical attention. "
                "Please visit the nearest hospital or contact emergency services immediately."
            ),

            "possible_disease": "Possible Emergency",

            "severity": "High",

            "see_doctor": True,

            "emergency": True
        }

    # Build past medical history

    history_text = ""

    if past_history:

        history_text = "\nPast Medical History:\n"

        for rec in past_history[:3]:

            history_text += (
                f"- {rec['possible_disease']}\n"
            )

    # User context

    state_text = json.dumps(
        conversation_state,
        indent=2,
        ensure_ascii=False
    ) if conversation_state else "No state available"

    session_context_summary = build_session_context_summary(session_context)

    user_context = f"""
        Patient Information:
        - Age: {age}
        - Gender: {gender}
        Structured Medical Profile:
        {structured_profile}

        Long-Term Medical Memory:
        {summary_memory}

        Mem0 Patient Memory:
        {long_term_memory}

        Dialogue State:
        {state_text}

        Relevant Previous Similar Cases:
        {vector_context}

        Recent Medical Conversation Context:
        {medical_context}

        Past Medical History:
        {history_text}

        Current Symptoms:
        {symptoms}

        {session_context_summary}

        Session Context:
        {session_context}

        Instructions:
        - If this user message answers a previous question, continue the same assessment.
        - Do not restart the symptom conversation if the pending question is already answered.
        - Do not ask again for information the user already provided, including body location, onset, duration, severity, and symptom quality.
        - If the user already stated the pain location (for example: left hand), do not ask where it is again.
        - Use the current active topic and pending slots from the dialogue state.
        """

    # Build messages

    messages = [

        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # Add recent conversation memory

    if conversation_history:

        for msg in conversation_history[-6:]:

            messages.append({

                "role": msg["role"],

                "content": msg["content"]
            })

    # Add current user message

    messages.append({

        "role": "user",

        "content": user_context
    })

    # Generate conversational response

    response = get_llm_response(

        messages,

        model=GROQ_MAIN_MODEL,

        temperature=TEMP_SYMPTOM,

        max_tokens=MAX_TOKENS_SYMPTOM
    )

    # Extract hidden medical metadata

    medical_data = extract_medical_info(
        symptoms,
        response,
        emergency
    )

    return {

        "response": response,

        "possible_disease": medical_data["possible_disease"],

        "severity": medical_data["severity"],

        "see_doctor": medical_data["see_doctor"],

        "emergency": medical_data["emergency"]
    }


def extract_medical_info(
    symptoms: str,
    ai_response: str,
    emergency: bool
) -> dict:

    txt = (
        symptoms + " " + ai_response
    ).lower()

    possible_disease = "general illness"

    severity = "Low"

    see_doctor = False

    # Disease extraction

    if any(word in txt for word in [

        "viral",
        "fever",
        "infection"

    ]):

        possible_disease = "viral infection"


    if any(word in txt for word in [

        "throat",
        "swallow",
        "pharyngitis"

    ]):

        possible_disease = "viral pharyngitis"


    if any(word in txt for word in [

        "allergy",
        "rash",
        "itching"

    ]):

        possible_disease = "allergy"


    # Severity detection

    if any(word in txt for word in [

        "chest pain",
        "difficulty breathing",
        "emergency"

    ]):

        severity = "High"

        see_doctor = True


    elif any(word in txt for word in [

        "fever",
        "pain",
        "infection"

    ]):

        severity = "Medium"

        see_doctor = True


    return {

        "possible_disease": possible_disease,

        "severity": severity,

        "see_doctor": see_doctor,

        "emergency": emergency
    }


def detect_emergency(symptoms: str) -> bool:

    txt = symptoms.lower()

    for rule in EMERGENCY_KEYWORDS:

        if all(keyword in txt for keyword in rule):

            return True

    return False