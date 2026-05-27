import json
from typing import Annotated, Any, Dict, TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, START, END

from agents.language_agent import LanguageAgent
from agents.conversation_state_agent import ConversationStateAgent
from agents.planner_agent import PlannerAgent
from agents.symptom_agent import SymptomAgent
from agents.health_data_agent import HealthDataAgent
from agents.education_agent import EducationAgent
from agents.outbreak_agent import OutbreakAgent
from agents.reasoning_agent import ReasoningAgent
from agents.rag_agent import RAGAgent
from agents.memory_agent import MemoryAgent
from agents.profile_memory_agent import ProfileMemoryAgent
from agents.memory_selector_agent import MemorySelectorAgent
from agents.synthesis_agent import SynthesisAgent
from agents.location_agent import LocationAgent

from database.login_manager import get_user, update_last_active
from database.conversation_manager import save_message
from database.models import DialogueState, Conversation, engine
from sqlalchemy.orm import Session

from tools.memory_manager import MemoryManager
from tools.redis_session_memory import RedisSessionMemory
from tools.mem0_client import Mem0Client
from tools.session_context_manager import SessionContextManager
from tools.vector_memory_tool import VectorMemory
from tools.context_memory_tool import build_medical_context

from config.settings import get_llm_response, GROQ_MAIN_MODEL, REDIS_URL, MEM0_API_KEY
from config.logger import logger

from data.vague_symptoms_keywords import vague_symptoms_keywords
from data.vaccination_keywords import vaccination_keywords
from data.vague_education_keywords import vague_education_keywords


# ═════════════════════════════════════════════════════
# STATE DEFINITION
# ═════════════════════════════════════════════════════

class ConversationState(TypedDict):
    """State graph for healthcare conversation"""
    phone_number: str
    conversation_id: int | None
    user_input: str
    detected_lang: str
    english_text: str
    response_style: str

    # User info
    user_name: str
    age: int
    gender: str
    pincode: str
    location_area: str
    pref_lang: str

    # Memory and context
    conversation_history: list
    summary_memory: str
    structured_profile: str
    medical_context: str
    vector_context: str
    long_term_memory: str

    # Dialogue state
    dialogue_state: dict
    last_assistant_message: str
    session_context: dict  # Latent internal session state

    # Plan
    execution_plan: list
    agent_outputs: dict

    # Final response
    response_english: str
    final_response: str
    outbreak_prefix: str

    # Flags
    check_outbreak_on_start: bool
    is_special_command: bool


# ═════════════════════════════════════════════════════
# LANGGRAPH COORDINATOR
# ═════════════════════════════════════════════════════

class LangGraphCoordinator:
    """
    Stateful healthcare conversation coordinator using LangGraph.
    Replaces the old Coordinator with proper dialogue state management.
    """

    def __init__(self):
        self.language_agent = LanguageAgent()
        self.conversation_state_agent = ConversationStateAgent()
        self.planner_agent = PlannerAgent()
        self.symptom_agent = SymptomAgent()
        self.health_data_agent = HealthDataAgent()
        self.education_agent = EducationAgent()
        self.outbreak_agent = OutbreakAgent()
        self.reasoning_agent = ReasoningAgent()
        self.rag_agent = RAGAgent()
        self.memory_agent = MemoryAgent()
        self.profile_memory_agent = ProfileMemoryAgent()
        self.memory_selector_agent = MemorySelectorAgent()
        self.synthesis_agent = SynthesisAgent()
        self.location_agent = LocationAgent()

        self.memory_manager = MemoryManager()
        self.redis_memory = RedisSessionMemory(redis_url=REDIS_URL)
        self.mem0_client = Mem0Client(api_key=MEM0_API_KEY)
        self.session_context_manager = None
        self.vector_memory = VectorMemory()

        # In-memory dialogue state cache per phone_number (session-level)
        self.dialogue_state_cache = {}
        
        # Session context cache per phone_number
        self.session_context_cache = {}

        # Initialize LangGraph
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile()

    def _build_graph(self):
        """Build LangGraph state machine"""
        graph = StateGraph(ConversationState)

        # Add nodes
        graph.add_node("input_validation", self._node_input_validation)
        graph.add_node("language_processing", self._node_language_processing)
        graph.add_node("init_session_context", self._node_init_session_context)
        graph.add_node("load_memory", self._node_load_memory)
        graph.add_node("update_dialogue_state", self._node_update_dialogue_state)
        graph.add_node("check_special_commands", self._node_check_special_commands)
        graph.add_node("outbreak_check", self._node_outbreak_check)
        graph.add_node("create_plan", self._node_create_plan)
        graph.add_node("execute_agents", self._node_execute_agents)
        graph.add_node("synthesize_response", self._node_synthesize_response)
        graph.add_node("translate_response", self._node_translate_response)
        graph.add_node("save_response", self._node_save_response)

        # Define edges
        graph.add_edge(START, "input_validation")
        graph.add_edge("input_validation", "language_processing")
        graph.add_edge("language_processing", "init_session_context")
        graph.add_edge("init_session_context", "load_memory")
        graph.add_edge("load_memory", "update_dialogue_state")
        graph.add_edge("update_dialogue_state", "check_special_commands")

        # Conditional: special command or normal flow
        graph.add_conditional_edges(
            "check_special_commands",
            lambda state: "special_command" if state.get("is_special_command") else "outbreak_check",
            {"special_command": "save_response", "outbreak_check": "outbreak_check"}
        )

        graph.add_edge("outbreak_check", "create_plan")
        graph.add_edge("create_plan", "execute_agents")
        graph.add_edge("execute_agents", "synthesize_response")
        graph.add_edge("synthesize_response", "translate_response")
        graph.add_edge("translate_response", "save_response")
        graph.add_edge("save_response", END)

        return graph

    def _node_input_validation(self, state: ConversationState) -> ConversationState:
        """Validate user and input"""
        user = get_user(state["phone_number"])
        if not user:
            state["final_response"] = "❌ User not registered. Please register first."
            return state

        update_last_active(state["phone_number"])
        return state

    def _node_language_processing(self, state: ConversationState) -> ConversationState:
        """Detect language and translate"""
        lang_result = self.language_agent.process_input(
            state["user_input"],
            state["pref_lang"]
        )

        state["detected_lang"] = lang_result["detected_language"]
        state["english_text"] = lang_result["english_text"]
        state["response_style"] = lang_result.get("response_style", "english")
        self.redis_memory.save_message(state["phone_number"], "user", state["user_input"])

        if state["conversation_id"]:
            save_message(state["conversation_id"], "user", state["user_input"])

        return state

    def _node_init_session_context(self, state: ConversationState) -> ConversationState:
        """Initialize or load session context"""
        phone_number = state["phone_number"]

        if phone_number in self.session_context_cache:
            self.session_context_manager = self.session_context_cache[phone_number]
            state["session_context"] = self.session_context_manager.get_full_context()
        else:
            existing_context = self.redis_memory.load_session_context(phone_number)
            if existing_context:
                if isinstance(existing_context, str):
                    existing_context = SessionContextManager.deserialize_from_storage(existing_context)
                manager = SessionContextManager(
                    phone_number=phone_number,
                    conversation_id=state["conversation_id"]
                )
                manager.load_or_create(existing_context)
                self.session_context_manager = manager
                self.session_context_cache[phone_number] = manager
                state["session_context"] = self.session_context_manager.get_full_context()
            else:
                self.session_context_manager = SessionContextManager(
                    phone_number=phone_number,
                    conversation_id=state["conversation_id"]
                )
                ctx = self.session_context_manager.initialize_context()
                state["session_context"] = ctx
                self.session_context_cache[phone_number] = self.session_context_manager

        self.session_context_manager.increment_turn()
        return state

    def _node_load_memory(self, state: ConversationState) -> ConversationState:
        """Load conversation history and memory"""
        history = []

        if state["conversation_history"]:
            history = state["conversation_history"]
        elif state["conversation_id"]:
            history = self.memory_manager.get_recent_messages(
                conversation_id=state["conversation_id"],
                limit=10
            )
            if not history:
                history = self.redis_memory.get_recent_messages(state["phone_number"], limit=20)
        else:
            history = self.redis_memory.get_recent_messages(state["phone_number"], limit=20)

        state["conversation_history"] = history or []

        if state["conversation_id"]:
            state["summary_memory"] = self.memory_manager.get_summary(state["conversation_id"]) or ""

        state["structured_profile"] = self.memory_manager.get_medical_profile(state["phone_number"]) or ""

        mem0_results = self.mem0_client.search(
            user_id=state["phone_number"],
            query=state["english_text"],
            top_k=5
        )

        state["long_term_memory"] = "\n".join(
            self.mem0_client.format_search_results(mem0_results)
        ) if mem0_results else ""

        return state

    def _node_update_dialogue_state(self, state: ConversationState) -> ConversationState:
        """Update dialogue state from cache, Redis, database, or create new"""
        phone_number = state["phone_number"]

        dialogue_state = None

        # 1. In-memory cache first
        if phone_number in self.dialogue_state_cache:
            dialogue_state = self.dialogue_state_cache[phone_number].copy()

        # 2. Redis session dialogue state fallback
        if dialogue_state is None:
            dialogue_state = self.redis_memory.load_dialogue_state(phone_number)

        # 3. Database persistent dialogue state if available
        persisted_state = None
        if dialogue_state is None and state["conversation_id"]:
            db_session = Session(engine)
            persisted_state = db_session.query(DialogueState).filter_by(
                conversation_id=state["conversation_id"]
            ).first()
            if persisted_state:
                dialogue_state = {
                    "active_topic": persisted_state.active_topic,
                    "task": persisted_state.task,
                    "stage": persisted_state.stage,
                    "state": persisted_state.state,
                    "continue_context": persisted_state.continue_context,
                    "is_answer_to_question": persisted_state.is_answer_to_question,
                    "last_assistant_question": persisted_state.last_assistant_question,
                    "pending_question": json.loads(persisted_state.pending_question),
                    "slots": json.loads(persisted_state.slots),
                    "pending_slots": json.loads(persisted_state.pending_slots),
                    "next_action": persisted_state.next_action,
                    "note": persisted_state.note,
                }
            db_session.close()

        if dialogue_state is None:
            dialogue_state = {
                "active_topic": "",
                "task": "symptom_assessment",
                "stage": "detail_collection",
                "state": "NEW_TOPIC",
                "continue_context": True,
                "is_answer_to_question": False,
                "last_assistant_question": "",
                "pending_question": {"id": "", "slot": "", "question": ""},
                "slots": {},
                "pending_slots": [],
                "next_action": "continue_assessment",
                "note": "",
            }

        # Get last assistant message
        last_assistant_message = ""
        if state["conversation_history"]:
            for msg in reversed(state["conversation_history"]):
                if msg["role"] == "assistant":
                    last_assistant_message = msg["content"]
                    break

        updated_dialogue_state = self.conversation_state_agent.update_state(
            state["english_text"],
            state["conversation_history"],
            previous_state=dialogue_state,
            last_assistant_message=last_assistant_message,
            session_memory=state["conversation_history"],
            long_term_memory=state.get("long_term_memory", ""),
            session_context=state.get("session_context")
        )

        state["dialogue_state"] = updated_dialogue_state
        state["last_assistant_message"] = last_assistant_message

        # ═══ RECORD IN SESSION CONTEXT ═══
        # Track pending question if one exists
        pending_q = updated_dialogue_state.get("pending_question", {})
        if pending_q.get("slot"):
            self.session_context_manager.record_slot_asked(
                pending_q["slot"],
                state["session_context"]["session_state"]["turn_count"],
                pending_q.get("question", "")
            )

        # Track filled slots
        for slot_name, slot_value in updated_dialogue_state.get("slots", {}).items():
            if slot_value:
                self.session_context_manager.record_slot_answered(
                    slot_name,
                    state["session_context"]["session_state"]["turn_count"],
                    str(slot_value)
                )

        # Update session context
        self.session_context_manager.update_dialogue_frame(updated_dialogue_state)
        state["session_context"] = self.session_context_manager.get_full_context()
        self.redis_memory.save_dialogue_state(phone_number, updated_dialogue_state)
        self.redis_memory.save_session_context(
            phone_number,
            self.session_context_manager.serialize_for_storage()
        )

        # 5. Save to in-memory cache too
        self.dialogue_state_cache[phone_number] = updated_dialogue_state

        # 6. Also persist to database if conversation_id exists
        if state["conversation_id"]:
            db_session = Session(engine)
            persisted_state = db_session.query(DialogueState).filter_by(
                conversation_id=state["conversation_id"]
            ).first()

            if persisted_state:
                persisted_state.active_topic = updated_dialogue_state["active_topic"]
                persisted_state.task = updated_dialogue_state["task"]
                persisted_state.stage = updated_dialogue_state["stage"]
                persisted_state.state = updated_dialogue_state["state"]
                persisted_state.continue_context = updated_dialogue_state["continue_context"]
                persisted_state.is_answer_to_question = updated_dialogue_state["is_answer_to_question"]
                persisted_state.last_assistant_question = updated_dialogue_state["last_assistant_question"]
                persisted_state.pending_question = json.dumps(updated_dialogue_state["pending_question"])
                persisted_state.slots = json.dumps(updated_dialogue_state["slots"])
                persisted_state.pending_slots = json.dumps(updated_dialogue_state["pending_slots"])
                persisted_state.next_action = updated_dialogue_state["next_action"]
                persisted_state.note = updated_dialogue_state["note"]
                persisted_state.updated_at = datetime.utcnow()
            else:
                new_state = DialogueState(
                    conversation_id=state["conversation_id"],
                    phone_number=state["phone_number"],
                    active_topic=updated_dialogue_state["active_topic"],
                    task=updated_dialogue_state["task"],
                    stage=updated_dialogue_state["stage"],
                    state=updated_dialogue_state["state"],
                    continue_context=updated_dialogue_state["continue_context"],
                    is_answer_to_question=updated_dialogue_state["is_answer_to_question"],
                    last_assistant_question=updated_dialogue_state["last_assistant_question"],
                    pending_question=json.dumps(updated_dialogue_state["pending_question"]),
                    slots=json.dumps(updated_dialogue_state["slots"]),
                    pending_slots=json.dumps(updated_dialogue_state["pending_slots"]),
                    next_action=updated_dialogue_state["next_action"],
                    note=updated_dialogue_state["note"],
                )
                db_session.add(new_state)

            db_session.commit()
            db_session.close()

        return state

    def _node_check_special_commands(self, state: ConversationState) -> ConversationState:
        """Check for special commands"""
        txt = state["english_text"].lower().strip()

        if any(k in txt for k in ["my history", "past records", "health history"]):
            result = self.health_data_agent.get_history(state["phone_number"])
            state["final_response"] = self.language_agent.translate_response(
                result["formatted_summary"],
                state["detected_lang"],
                state["response_style"]
            )
            state["is_special_command"] = True
            return state

        if any(k in txt for k in ["health tip", "daily tip", "tip"]):
            tip = self.education_agent.daily_tip(state["user_name"])
            state["final_response"] = self.language_agent.translate_response(
                tip,
                state["detected_lang"],
                state["response_style"]
            )
            state["is_special_command"] = True
            return state

        state["is_special_command"] = False
        return state

    def _node_outbreak_check(self, state: ConversationState) -> ConversationState:
        """Check for outbreak alerts"""
        if state["check_outbreak_on_start"]:
            alert = self.outbreak_agent.check_area_outbreaks(
                state["pincode"],
                state["detected_lang"]
            )
            if alert:
                translated_alert = self.language_agent.translate_response(
                    alert,
                    state["detected_lang"]
                )
                state["outbreak_prefix"] = (
                    f"⚠️ *Health Alert for your area:*\n"
                    f"{translated_alert}\n\n{'─'*30}\n\n"
                )
        return state

    def _node_create_plan(self, state: ConversationState) -> ConversationState:
        """Create execution plan"""
        plan = self.planner_agent.create_plan(
            original_input=state["user_input"],
            english_input=state["english_text"],
            history=state["conversation_history"],
            conversation_state=state["dialogue_state"],
            long_term_memory=state.get("long_term_memory", "")
        )

        state["execution_plan"] = plan
        logger.info(f"Execution Plan: {plan}")
        state["agent_outputs"] = {}
        return state

    def _node_execute_agents(self, state: ConversationState) -> ConversationState:
        """Execute agents based on plan"""
        agent_outputs = {}

        for step in state["execution_plan"]:
            tool = step.get("tool")

            if tool == "symptom_analysis":
                medical_context = build_medical_context(state["conversation_history"])
                similar_memories = self.vector_memory.search_memory(state["english_text"], k=5)
                ranked_memories = self.memory_selector_agent.rank_memories(
                    state["english_text"],
                    similar_memories,
                    top_k=3
                )
                vector_context = "\n".join([m["text"] for m in ranked_memories])

                symptom_result = self.symptom_agent.analyze(
                    symptoms_english=state["english_text"],
                    phone_number=state["phone_number"],
                    user_name=state["user_name"],
                    age=state["age"],
                    gender=state["gender"],
                    conversation_history=state["conversation_history"],
                    medical_context=medical_context,
                    summary_memory=state["summary_memory"],
                    vector_context=vector_context,
                    structured_profile=state["structured_profile"],
                    long_term_memory=state.get("long_term_memory", ""),
                    conversation_state=state["dialogue_state"],
                    session_context=state.get("session_context")
                )

                reasoning = self.reasoning_agent.analyze_response(
                    state["english_text"],
                    symptom_result
                )

                final_response = symptom_result["response"]
                if reasoning.get("needs_followup"):
                    followup = reasoning.get("followup_question", "")
                    if followup:
                        final_response += f"\n\n{followup}"

                agent_outputs["symptom_analysis"] = {
                    **symptom_result,
                    "response": final_response
                }

            elif tool == "vaccination_rag":
                rag_result = self.rag_agent.answer(state["english_text"])
                agent_outputs["medical_knowledge"] = rag_result

            elif tool == "disease_education":
                education_result = self.education_agent.educate(
                    state["english_text"],
                    state["user_name"]
                )
                agent_outputs["education"] = education_result

            elif tool == "outbreak_check":
                outbreak_result = self.outbreak_agent.check_area_outbreaks(
                    state["pincode"],
                    state["detected_lang"]
                )
                if outbreak_result:
                    agent_outputs["outbreak_alert"] = outbreak_result

            elif tool == "hospital_search":
                # Extract coordinates from user's WhatsApp location or pincode/city
                import asyncio
                from concurrent.futures import ThreadPoolExecutor
                
                def run_in_new_loop():
                    """Run async code in a separate thread with its own event loop"""
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            self.location_agent.analyze(
                                query=state["english_text"],
                                phone_number=state["phone_number"],
                                user_name=state["user_name"],
                                pincode=state["pincode"],
                                latitude=state.get("whatsapp_latitude"),
                                longitude=state.get("whatsapp_longitude"),
                                conversation_history=state["conversation_history"],
                                medical_context=state.get("medical_context", ""),
                                long_term_memory=state.get("long_term_memory", ""),
                            )
                        )
                    finally:
                        new_loop.close()
                
                try:
                    # Check if there's already a running event loop
                    asyncio.get_running_loop()
                    # If we get here, run in a thread to avoid conflict
                    with ThreadPoolExecutor() as executor:
                        location_result = executor.submit(run_in_new_loop).result()
                except RuntimeError:
                    # No running event loop, safe to use asyncio.run()
                    location_result = run_in_new_loop()
                
                agent_outputs["hospital_search"] = location_result

        if not agent_outputs:
            medical_context = build_medical_context(state["conversation_history"])
            similar_memories = self.vector_memory.search_memory(state["english_text"], k=5)
            ranked_memories = self.memory_selector_agent.rank_memories(
                state["english_text"],
                similar_memories,
                top_k=3
            )
            vector_context = "\n".join([m["text"] for m in ranked_memories])

            fallback_result = self.symptom_agent.analyze(
                symptoms_english=state["english_text"],
                phone_number=state["phone_number"],
                user_name=state["user_name"],
                age=state["age"],
                gender=state["gender"],
                conversation_history=state["conversation_history"],
                medical_context=medical_context,
                summary_memory=state["summary_memory"],
                vector_context=vector_context,
                structured_profile=state["structured_profile"],
                long_term_memory=state.get("long_term_memory", ""),
                conversation_state=state["dialogue_state"],
                session_context=state.get("session_context")
            )

            agent_outputs["fallback_symptom_analysis"] = fallback_result

        state["agent_outputs"] = agent_outputs
        return state

    def _node_synthesize_response(self, state: ConversationState) -> ConversationState:
        """Synthesize agent outputs into single response"""
        hospital_search_output = state["agent_outputs"].get("hospital_search")
        if hospital_search_output:
            allowed_keys = {"hospital_search", "outbreak_alert"}
            if set(state["agent_outputs"].keys()).issubset(allowed_keys):
                direct_response = (
                    hospital_search_output.get("full_response")
                    or hospital_search_output.get("message")
                    or hospital_search_output.get("response")
                )
                if direct_response:
                    state["response_english"] = direct_response
                    return state

        response_english = self.synthesis_agent.synthesize(
            state["english_text"],
            state["agent_outputs"],
            session_context=state.get("session_context")
        )

        state["response_english"] = response_english
        return state

    def _node_translate_response(self, state: ConversationState) -> ConversationState:
        """Translate response to user's language"""
        final = self.language_agent.translate_response(
            state["response_english"],
            state["detected_lang"],
            state["response_style"]
        )

        state["final_response"] = state["outbreak_prefix"] + final
        return state

    def _node_save_response(self, state: ConversationState) -> ConversationState:
        """Save response and memories"""
        if state["conversation_id"]:
            save_message(
                state["conversation_id"],
                "assistant",
                state["final_response"]
            )

        # Store vector memory
        try:
            memory_text = f"""
                User Query: {state["english_text"]}
                Assistant Response: {state["final_response"]}
            """
            self.vector_memory.add_memory(
                memory_text,
                metadata={"phone_number": state["phone_number"]}
            )

            profile = self.profile_memory_agent.extract_profile(memory_text)
            self.memory_manager.save_medical_profile(state["phone_number"], profile)
        except Exception as e:
            logger.error(f"Vector memory save failed: {str(e)}")

        # Auto-summarize if needed
        try:
            if state["conversation_id"]:
                recent_msgs = self.memory_manager.get_recent_messages(
                    state["conversation_id"],
                    limit=20
                )
                if len(recent_msgs) >= 20:
                    summary = self.memory_agent.summarize_conversation(recent_msgs)
                    self.memory_manager.save_summary(state["conversation_id"], summary)
        except Exception as e:
            logger.error(f"Memory summarization failed: {str(e)}")

        self.redis_memory.save_message(state["phone_number"], "assistant", state["final_response"])
        return state

    def handle_message(
        self,
        phone_number: str,
        user_input: str,
        conversation_id: int = None,
        chat_history: list = None,
        check_outbreak_on_start: bool = False,
    ) -> str:
        """Main entry point for handling user messages"""

        user = get_user(phone_number)
        if not user:
            return "❌ User not registered. Please register first."

        # Initialize state
        initial_state: ConversationState = {
            "phone_number": phone_number,
            "conversation_id": conversation_id,
            "user_input": user_input,
            "detected_lang": "",
            "english_text": "",
            "response_style": "english",
            "user_name": user["name"],
            "age": user["age"],
            "gender": user["gender"],
            "pincode": user["pincode"],
            "location_area": user["location_area"],
            "pref_lang": user["language"],
            "conversation_history": chat_history or [],
            "summary_memory": "",
            "structured_profile": "",
            "medical_context": "",
            "vector_context": "",
            "long_term_memory": "",
            "session_context": {},
            "dialogue_state": {},
            "last_assistant_message": "",
            "execution_plan": [],
            "agent_outputs": {},
            "response_english": "",
            "final_response": "",
            "outbreak_prefix": "",
            "check_outbreak_on_start": check_outbreak_on_start,
            "is_special_command": False,
        }

        # Execute graph with checkpointing
        final_state = self.compiled_graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": str(conversation_id) if conversation_id else phone_number}}
        )

        return final_state["final_response"]
