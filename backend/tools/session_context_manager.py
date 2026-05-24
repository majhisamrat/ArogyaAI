import copy
import json
from datetime import datetime
from typing import Dict, List, Optional
from config.logger import logger


class SessionContextManager:
    """
    Manages latent internal session state across turns.
    Prevents re-asking questions, tracks goal progress, supports multi-pass reasoning.
    
    Separates:
    - Chat history (what was said)
    - Session context (what was learned/decided)
    - Dialogue frame (active topic, pending questions, slots)
    """

    def __init__(self, phone_number: str, conversation_id: Optional[int] = None):
        self.phone_number = phone_number
        self.conversation_id = conversation_id
        self.cache = {}

    def initialize_context(self) -> Dict:
        """Create fresh session context"""
        context = {
            "conversation_id": self.conversation_id,
            "phone_number": self.phone_number,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),

            # ═══ EXPLICIT DIALOGUE FRAME ═══
            "dialogue_frame": {
                "active_topic": "",
                "task": "symptom_assessment",
                "stage": "detail_collection",
                "state": "NEW_TOPIC",
                "pending_question": {"id": "", "slot": "", "question": ""},
                "slots": {},
                "pending_slots": [],
                "next_action": "continue_assessment",
            },

            # ═══ LATENT SESSION STATE ═══
            "session_state": {
                "turn_count": 0,
                "slot_history": {},  # slot -> {"asked_at_turn": N, "answered_at_turn": M, "value": V}
                "asked_slots": set(),  # slots already asked (prevents re-asking)
                "unanswered_slots": [],  # slots user didn't answer
                "last_user_intent": "",  # inferred intent from user
                "context_window": [],  # last 3 user turns (condensed)
                "extracted_facts": [],  # facts extracted this session
            },

            # ═══ TASK/GOAL MANAGEMENT ═══
            "goal_management": {
                "current_goal": "gather_symptoms",  # gather_symptoms | assess_severity | recommend_action
                "goal_progress": 0.0,  # 0-1
                "completed_tasks": [],
                "failed_tasks": [],
                "goal_history": [],  # [{goal, progress, timestamp}]
            },

            # ═══ POLICY-DRIVEN ACTIONS ═══
            "policy_state": {
                "next_action_policy": "continue_assessment",
                "confidence_in_assessment": 0.0,  # 0-1
                "reasoning_chain": [],  # [{"step": "...", "decision": "...", "turn": N}]
                "multi_pass_results": {},  # results from multi-pass reasoning
            },

            # ═══ CONTEXT CONDENSATION ═══
            "context_condensation": {
                "full_history_turns": 0,
                "condensed_at_turn": 0,
                "summary": "",
            },
        }
        self.cache = context
        return context

    def load_or_create(self, previous_context: Optional[Dict] = None) -> Dict:
        """Load existing context or create new"""
        if previous_context:
            if isinstance(previous_context.get("session_state", {}).get("asked_slots"), list):
                previous_context["session_state"]["asked_slots"] = set(
                    previous_context["session_state"]["asked_slots"]
                )
            self.cache = previous_context
            return self.cache
        return self.initialize_context()

    def increment_turn(self):
        """Increment turn count and update timestamp"""
        self.cache["session_state"]["turn_count"] += 1
        self.cache["updated_at"] = datetime.utcnow().isoformat()

    def record_slot_asked(self, slot_name: str, turn: int, question: str):
        """Record that a slot was asked"""
        if slot_name not in self.cache["session_state"]["asked_slots"]:
            self.cache["session_state"]["asked_slots"].add(slot_name)
            self.cache["session_state"]["slot_history"][slot_name] = {
                "asked_at_turn": turn,
                "question": question,
                "answered": False,
                "answered_at_turn": None,
                "value": None,
            }
            logger.info(f"[SessionContext] Recorded slot asked: {slot_name} (turn {turn})")

    def record_slot_answered(self, slot_name: str, turn: int, value: str):
        """Record that a slot was answered"""
        if slot_name in self.cache["session_state"]["slot_history"]:
            self.cache["session_state"]["slot_history"][slot_name].update({
                "answered": True,
                "answered_at_turn": turn,
                "value": value,
            })
            if slot_name in self.cache["session_state"]["unanswered_slots"]:
                self.cache["session_state"]["unanswered_slots"].remove(slot_name)
            logger.info(f"[SessionContext] Recorded slot answered: {slot_name} = {value} (turn {turn})")

    def was_slot_already_asked(self, slot_name: str) -> bool:
        """Check if slot was already asked in this session"""
        return slot_name in self.cache["session_state"]["asked_slots"]

    def get_unanswered_slots(self) -> List[str]:
        """Get slots that were asked but not answered"""
        return self.cache["session_state"]["unanswered_slots"]

    def update_dialogue_frame(self, frame_update: Dict):
        """Update explicit dialogue frame"""
        self.cache["dialogue_frame"].update(frame_update)
        self.cache["updated_at"] = datetime.utcnow().isoformat()

    def update_goal(self, new_goal: str, progress: float, reasoning: str = ""):
        """Update task/goal and progress"""
        old_goal = self.cache["goal_management"]["current_goal"]
        
        self.cache["goal_management"]["current_goal"] = new_goal
        self.cache["goal_management"]["goal_progress"] = min(1.0, progress)
        
        self.cache["goal_management"]["goal_history"].append({
            "from_goal": old_goal,
            "to_goal": new_goal,
            "progress": progress,
            "turn": self.cache["session_state"]["turn_count"],
            "reasoning": reasoning,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def set_next_action_policy(
        self,
        policy: str,
        confidence: float,
        reasoning: str = ""
    ):
        """Set policy-driven next action with confidence"""
        self.cache["policy_state"]["next_action_policy"] = policy
        self.cache["policy_state"]["confidence_in_assessment"] = confidence
        
        self.cache["policy_state"]["reasoning_chain"].append({
            "turn": self.cache["session_state"]["turn_count"],
            "policy": policy,
            "confidence": confidence,
            "reasoning": reasoning,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def store_multi_pass_result(self, pass_name: str, result: Dict):
        """Store result from multi-pass reasoning"""
        self.cache["policy_state"]["multi_pass_results"][pass_name] = {
            "result": result,
            "turn": self.cache["session_state"]["turn_count"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def add_to_context_window(self, user_message: str, assistant_response: str = ""):
        """Add condensed turn to context window (keep last 3)"""
        window = self.cache["session_state"]["context_window"]
        window.append({
            "turn": self.cache["session_state"]["turn_count"],
            "user": user_message[:100],  # truncate
            "assistant": assistant_response[:100],
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Keep only last 3 turns
        self.cache["session_state"]["context_window"] = window[-3:]

    def extract_fact(self, fact: str):
        """Extract and store a fact from conversation"""
        self.cache["session_state"]["extracted_facts"].append({
            "fact": fact,
            "turn": self.cache["session_state"]["turn_count"],
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_dialogue_frame(self) -> Dict:
        """Get current dialogue frame"""
        return self.cache["dialogue_frame"]

    def get_session_state(self) -> Dict:
        """Get latent session state"""
        return self.cache["session_state"]

    def get_goal_state(self) -> Dict:
        """Get goal management state"""
        return self.cache["goal_management"]

    def get_policy_state(self) -> Dict:
        """Get policy-driven decision state"""
        return self.cache["policy_state"]

    def get_full_context(self) -> Dict:
        """Get entire session context for LLM reasoning"""
        return self.cache

    def serialize_for_storage(self) -> str:
        """Serialize context for Redis/DB storage"""
        context_copy = copy.deepcopy(self.cache)
        asked_slots = context_copy["session_state"].get("asked_slots")
        if isinstance(asked_slots, set):
            context_copy["session_state"]["asked_slots"] = list(asked_slots)
        return json.dumps(context_copy, default=str)

    @staticmethod
    def deserialize_from_storage(json_str: str) -> Dict:
        """Deserialize context from Redis/DB storage"""
        context = json.loads(json_str)
        # Convert asked_slots back to set
        if isinstance(context["session_state"]["asked_slots"], list):
            context["session_state"]["asked_slots"] = set(
                context["session_state"]["asked_slots"]
            )
        return context

    def create_context_summary(self) -> str:
        """Create condensed summary of session for context window"""
        facts = self.cache["session_state"]["extracted_facts"]
        slots = self.cache["dialogue_frame"]["slots"]
        goal = self.cache["goal_management"]["current_goal"]

        summary = f"""
Session Summary:
- Goal: {goal} ({self.cache['goal_management']['goal_progress']*100:.0f}% progress)
- Turns: {self.cache['session_state']['turn_count']}
- Extracted Facts: {len(facts)}
- Filled Slots: {len(slots)}
- Active Topic: {self.cache['dialogue_frame']['active_topic']}
"""
        return summary.strip()
