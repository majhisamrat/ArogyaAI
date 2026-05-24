from database.models import (
    ConversationMemory,
    MedicalMemory,
    Message,
    engine
)
from database.models import MedicalMemory
from database.login_manager import get_user
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)


class MemoryManager:

    def __init__(self):
        self.db = Session()

    # RECENT CHAT
    def get_recent_messages(
        self,
        conversation_id,
        limit=10
    ):

        msgs = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id
            )
            .order_by(Message.timestamp.desc())
            .limit(limit)
            .all()
        )

        msgs.reverse()

        return [
            {
                "role": m.role,
                "content": m.content
            }
            for m in msgs
        ]

        # SUMMARY MEMORY
    def get_summary(self, conversation_id):

        memory = (
            self.db.query(ConversationMemory)
            .filter(
                ConversationMemory.conversation_id
                == conversation_id
            )
            .order_by(
            ConversationMemory.created_at.desc()
                )
            .first()
        )

        return memory.summary if memory else ""
    # ─────────────────────────────────────
# STRUCTURED MEDICAL MEMORY
# ─────────────────────────────────────

    def save_medical_profile(
        self,
        phone_number,
        profile_data
    ):

        user = get_user(phone_number)

        if not user:
            return

        existing = (
            self.db.query(MedicalMemory)
            .filter(
                MedicalMemory.user_id == user["id"]
            )
            .first()
        )

        diseases = ", ".join(
            profile_data.get("diseases", [])
        )

        allergies = ", ".join(
            profile_data.get("allergies", [])
        )

        medications = ", ".join(
            profile_data.get("medications", [])
        )

        recurring = ", ".join(
            profile_data.get(
                "recurring_symptoms",
                []
            )
        )

        if existing:

            existing.diseases = diseases
            existing.allergies = allergies
            existing.medications = medications
            existing.recurring_symptoms = recurring

        else:

            mem = MedicalMemory(

                user_id=user["id"],

                diseases=diseases,

                allergies=allergies,

                medications=medications,

                recurring_symptoms=recurring
            )

            self.db.add(mem)

        self.db.commit()


    def get_medical_profile(
        self,
        phone_number
    ):

        user = get_user(phone_number)

        if not user:
            return ""

        mem = (
            self.db.query(MedicalMemory)
            .filter(
                MedicalMemory.user_id == user["id"]
            )
            .first()
        )

        if not mem:
            return ""

        return f'''
            Known Diseases:
            {mem.diseases}

            Allergies:
            {mem.allergies}

            Medications:
            {mem.medications}

            Recurring Symptoms:
            {mem.recurring_symptoms}
            '''

    # SAVE SUMMARY
    def save_summary(
        self,
        conversation_id,
        summary
    ):

        mem = ConversationMemory(
            conversation_id=conversation_id,
            summary=summary
        )

        self.db.add(mem)
        self.db.commit()