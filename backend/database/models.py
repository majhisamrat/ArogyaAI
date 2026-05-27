from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from config.settings import DATABASE_URL, BACKEND_DIR
from pathlib import Path
import os

# Create backend/data/ folder if not exists
db_dir = BACKEND_DIR / "data"
os.makedirs(db_dir, exist_ok=True)

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)


# ── Users Table ───────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    phone_number    = Column(String(20), unique=True, nullable=False)  # key identifier
    name            = Column(String(100), nullable=False)
    age             = Column(Integer, nullable=False)
    gender          = Column(String(10), nullable=False)               # Male/Female/Other
    pincode         = Column(String(10), nullable=False)
    location_area   = Column(String(100), nullable=True)               # fetched from pincode API
    language        = Column(String(10), default="en")                 # preferred language
    registered_at   = Column(DateTime, default=datetime.utcnow)
    last_active     = Column(DateTime, default=datetime.utcnow)

    # Relationships
    health_records  = relationship("HealthRecord", back_populates="user")

    def __repr__(self):
        return f"<User {self.name} | {self.phone_number} | Pincode: {self.pincode}>"


# ── Health Records Table ──────────────────────────────
class HealthRecord(Base):
    __tablename__ = "health_records"

    id               = Column(Integer, primary_key=True, autoincrement=True)

    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)

    symptoms         = Column(Text, nullable=False)

    possible_disease = Column(String(200), nullable=True)

    advice           = Column(Text, nullable=True)

    severity         = Column(String(20), nullable=True)

    confidence       = Column(Float, default=0.0)

    emergency        = Column(Boolean, default=False)

    language_used    = Column(String(10), default="en")

    timestamp        = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship(
        "User",
        back_populates="health_records"
    )

    def __repr__(self):

        return (
            f"<HealthRecord "
            f"User:{self.user_id} | "
            f"{self.possible_disease} | "
            f"Severity:{self.severity}>"
        )

    def __repr__(self):
        return f"<HealthRecord User:{self.user_id} | {self.possible_disease} | {self.timestamp}>"
    
# ── Conversations Table ──────────────────────────────

class Conversation(Base):

    __tablename__ = "conversations"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    title = Column(
        String(200),
        default="New Conversation"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete"
    )

    user = relationship("User")


    def __repr__(self):

        return f"<Conversation {self.id} | User:{self.user_id}>"



# ── Messages Table ───────────────────────────────────

class Message(Base):

    __tablename__ = "messages"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False
    )

    role = Column(
        String(20),
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    timestamp = Column(
        DateTime,
        default=datetime.utcnow
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )


    def __repr__(self):

        return f"<Message {self.role}>"


# ── Outbreak Logs Table ───────────────────────────────
class OutbreakLog(Base):
    __tablename__ = "outbreak_logs"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    pincode         = Column(String(10), nullable=False)
    location_area   = Column(String(100), nullable=True)
    disease         = Column(String(200), nullable=False)
    case_count      = Column(Integer, default=1)
    alert_sent      = Column(Boolean, default=False)
    reported_at     = Column(DateTime, default=datetime.utcnow)
    last_updated    = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<OutbreakLog {self.disease} | Pincode:{self.pincode} | Cases:{self.case_count}>"


# ── WhatsApp Registration State Table ─────────────────
# Tracks step-by-step registration progress on WhatsApp
class RegistrationState(Base):
    __tablename__ = "registration_states"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    phone_number    = Column(String(20), unique=True, nullable=False)
    current_step    = Column(String(50), default="waiting_name")
    # Steps: waiting_name → waiting_age → waiting_gender → waiting_pincode → complete
    temp_name       = Column(String(100), nullable=True)
    temp_age        = Column(String(5), nullable=True)
    temp_gender     = Column(String(10), nullable=True)
    temp_pincode    = Column(String(10), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RegistrationState {self.phone_number} | Step: {self.current_step}>"

# ── Conversation Summary Memory ─────────────────────

class ConversationMemory(Base):

    __tablename__ = "conversation_memory"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False
    )

    summary = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ── Structured Medical Memory ───────────────────────

class MedicalMemory(Base):

    __tablename__ = "medical_memory"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    diseases = Column(Text, default="")
    allergies = Column(Text, default="")
    medications = Column(Text, default="")
    recurring_symptoms = Column(Text, default="")

    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ── Dialogue State Table ────────────────────────────
class DialogueState(Base):

    __tablename__ = "dialogue_state"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False,
        unique=True
    )

    phone_number = Column(
        String(20),
        ForeignKey("users.phone_number"),
        nullable=False
    )

    # Dialogue frame fields
    active_topic = Column(Text, default="")
    task = Column(String(50), default="symptom_assessment")
    stage = Column(String(50), default="detail_collection")
    state = Column(String(50), default="NEW_TOPIC")

    # Boolean flags
    continue_context = Column(Boolean, default=True)
    is_answer_to_question = Column(Boolean, default=False)

    # Question tracking
    last_assistant_question = Column(Text, default="")
    pending_question = Column(Text, default="{}")  # JSON string

    # Slot tracking
    slots = Column(Text, default="{}")  # JSON string
    pending_slots = Column(Text, default="[]")  # JSON string

    # Action and metadata
    next_action = Column(String(50), default="continue_assessment")
    note = Column(Text, default="")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DialogueState Conv:{self.conversation_id} | State:{self.state} | Task:{self.task}>"


# ── Create All Tables ─────────────────────────────────
def init_db():
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully!")


if __name__ == "__main__":
    init_db()