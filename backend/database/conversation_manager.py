from database.db_handler import get_db_session

from database.models import (
    User,
    Conversation,
    Message
)

from datetime import datetime


# CREATE CONVERSATION
def create_conversation(
    phone_number: str,
    title: str = "New Chat"
):

    db = get_db_session()

    try:

        user = db.query(User).filter(
            User.phone_number == phone_number
        ).first()

        if not user:
            return None

        convo = Conversation(
            user_id=user.id,
            title=title
        )

        db.add(convo)

        db.commit()

        db.refresh(convo)

        return convo.id

    finally:

        db.close()


# SAVE MESSAGE

def save_message(
    conversation_id: int,
    role: str,
    content: str
):

    db = get_db_session()

    try:

        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )

        db.add(msg)

        convo = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if convo:

            convo.updated_at = datetime.utcnow()

        db.commit()

    finally:

        db.close()


# GET USER CONVERSATIONS

def get_user_conversations(
    phone_number: str
):

    db = get_db_session()

    try:

        user = db.query(User).filter(
            User.phone_number == phone_number
        ).first()

        if not user:
            return []

        conversations = db.query(
            Conversation
        ).filter(
            Conversation.user_id == user.id
        ).order_by(
            Conversation.updated_at.desc()
        ).all()

        result = []

        for c in conversations:

            result.append({
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            })

        return result

    finally:

        db.close()


# UPDATE CONVERSATION TITLE

def update_conversation_title(
    conversation_id: int,
    title: str
):
    """Update the title of a conversation."""

    db = get_db_session()

    try:

        convo = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if convo:
            convo.title = title[:200]  # Enforce DB column length
            db.commit()
            return True

        return False

    finally:

        db.close()


# GET CONVERSATION MESSAGES

def get_conversation_messages(
    conversation_id: int
):

    db = get_db_session()

    try:

        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(
            Message.timestamp.asc()
        ).all()

        result = []

        for m in messages:

            result.append({

                "id": m.id,

                "role": m.role,

                "content": m.content,

                "timestamp": m.timestamp.isoformat() if m.timestamp else None

            })

        return result

    finally:

        db.close()


# DELETE CONVERSATION
def delete_conversation(
    conversation_id: int
) -> bool:
    """Delete a conversation and all its messages from SQLite."""
    db = get_db_session()
    try:
        convo = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if convo:
            db.delete(convo)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()