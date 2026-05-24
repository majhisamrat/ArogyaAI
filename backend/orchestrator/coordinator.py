# from agents.language_agent import LanguageAgent
# from agents.symptom_agent import SymptomAgent
# from agents.health_data_agent import HealthDataAgent
# from agents.education_agent import EducationAgent
# from agents.outbreak_agent import OutbreakAgent
# from agents.planner_agent import PlannerAgent
# from agents.reasoning_agent import ReasoningAgent
# from agents.rag_agent import RAGAgent
# from agents.memory_agent import MemoryAgent
# from agents.profile_memory_agent import ProfileMemoryAgent
# from agents.memory_selector_agent import MemorySelectorAgent
# from agents.synthesis_agent import SynthesisAgent

# from database.login_manager import (
#     get_user,
#     update_last_active
# )

# from database.conversation_manager import (
#     save_message
# )

# from tools.memory_manager import MemoryManager
# from tools.vector_memory_tool import VectorMemory

# from config.settings import (
#     get_llm_response,
#     GROQ_MAIN_MODEL
# )

# from config.logger import logger

# from data.vague_symptoms_keywords import vague_symptoms_keywords
# from data.vaccination_keywords import vaccination_keywords
# from data.vague_education_keywords import vague_education_keywords
# from agents.conversation_state_agent import (
#     ConversationStateAgent
# )

# # ─────────────────────────────────────────────
# # Keywords
# # ─────────────────────────────────────────────

# VAGUE_SYMPTOMS = vague_symptoms_keywords
# VACCINATION_KEYWORDS = vaccination_keywords
# VAGUE_EDUCATION = vague_education_keywords


# class Coordinator:
#     """
#     Advanced Health AI Coordinator

#     Features:
#     - Multi-agent orchestration
#     - Long-term memory
#     - Vector retrieval
#     - Structured medical profile
#     - Intelligent memory selection
#     - Multi-agent synthesis
#     """

#     def __init__(self):

#         self.language_agent = LanguageAgent()
#         self.symptom_agent = SymptomAgent()
#         self.health_data_agent = HealthDataAgent()
#         self.education_agent = EducationAgent()
#         self.outbreak_agent = OutbreakAgent()
#         self.planner_agent = PlannerAgent()
#         self.reasoning_agent = ReasoningAgent()
#         self.rag_agent = RAGAgent()

#         self.memory_agent = MemoryAgent()
#         self.memory_manager = MemoryManager()

#         self.profile_memory_agent = ProfileMemoryAgent()
#         self.memory_selector_agent = MemorySelectorAgent()
#         self.synthesis_agent = SynthesisAgent()

#         self.vector_memory = VectorMemory()

#         self.conversation_state = {}
#         self.conversation_state_agent = ( ConversationStateAgent())

#     # ═══════════════════════════════════════════
#     # MAIN ENTRY
#     # ═══════════════════════════════════════════

#     def handle_message(
#         self,
#         phone_number: str,
#         user_input: str,
#         conversation_id: int = None,
#         chat_history: list = None,
#         check_outbreak_on_start: bool = False,
#         conversation_state=None
#     ) -> str:

#         user = get_user(phone_number)

#         if not user:
#             return "❌ User not registered. Please register first."

#         update_last_active(phone_number)

#         # SAVE USER MESSAGE

#         if conversation_id:

#             save_message(
#                 conversation_id,
#                 "user",
#                 user_input
#             )

#         # USER INFO

#         name = user["name"]
#         age = user["age"]
#         gender = user["gender"]
#         pincode = user["pincode"]
#         location_area = user["location_area"]
#         pref_lang = user["language"]

#         # ─────────────────────────────────────
#         # MEMORY SYSTEM
#         # ─────────────────────────────────────

#         recent_history = []

#         if conversation_id:

#             recent_history = self.memory_manager.get_recent_messages(
#                 conversation_id=conversation_id,
#                 limit=10
#             )

#         history = recent_history or chat_history or []

#         summary_memory = ""

#         if conversation_id:

#             summary_memory = self.memory_manager.get_summary(
#                 conversation_id
#             )

#         structured_profile = self.memory_manager.get_medical_profile(
#             phone_number
#         )

#         # ─────────────────────────────────────
#         # LANGUAGE PROCESSING
#         # ─────────────────────────────────────

#         lang_result = self.language_agent.process_input(
#             user_input,
#             pref_lang
#         )

#         detected_lang = lang_result["detected_language"]

#         response_style = lang_result.get(
#             "response_style",
#             "english"
#         )

#         english_text = lang_result["english_text"]

#         outbreak_prefix = ""

#         # ─────────────────────────────────────
#         # OUTBREAK ALERT
#         # ─────────────────────────────────────

#         if check_outbreak_on_start:

#             alert = self.outbreak_agent.check_area_outbreaks(
#                 pincode,
#                 detected_lang
#             )

#             if alert:

#                 translated_alert = self.language_agent.translate_response(
#                     alert,
#                     detected_lang
#                 )

#                 outbreak_prefix = (
#                     f"⚠️ *Health Alert for your area:*\n"
#                     f"{translated_alert}\n\n{'─'*30}\n\n"
#                 )

#         # ─────────────────────────────────────
#         # SPECIAL COMMANDS
#         # ─────────────────────────────────────

#         special = self._handle_special_commands(
#             english_text,
#             name,
#             detected_lang,
#             phone_number
#         )

#         if special:

#             final_response = outbreak_prefix + special

#             if conversation_id:

#                 save_message(
#                     conversation_id,
#                     "assistant",
#                     final_response
#                 )

#             return final_response

#         conversation_state = self._get_user_state(
#             phone_number
#         )

#         last_assistant_message = self._get_last_assistant_message(
#             history,
#             conversation_state
#         )

#         conversation_state = self.conversation_state_agent.update_state(
#             english_text,
#             history,
#             previous_state=conversation_state,
#             last_assistant_message=last_assistant_message
#         )

#         self.conversation_state[phone_number] = conversation_state
#         # ─────────────────────────────────────
#         # AI PLANNING
#         # ─────────────────────────────────────

#         plan = self.planner_agent.create_plan(
#             original_input=user_input,
#             english_input=english_text,
#             history=history,
#             conversation_state=conversation_state
#         )

#         logger.info(f"Execution Plan: {plan}")

#         # ─────────────────────────────────────
#         # MULTI-AGENT OUTPUT STORAGE
#         # ─────────────────────────────────────

#         agent_outputs = {}

#         # ─────────────────────────────────────
#         # EXECUTE PLAN
#         # ─────────────────────────────────────

#         for step in plan:

#             tool = step.get("tool")

#             # ─────────────────────────────────
#             # SYMPTOM ANALYSIS AGENT
#             # ─────────────────────────────────

#             if tool == "symptom_analysis":

#                 symptom_result = self._handle_symptom(

#                     english_text=english_text,

#                     phone_number=phone_number,

#                     name=name,

#                     age=age,

#                     gender=gender,

#                     pincode=pincode,

#                     location_area=location_area,

#                     detected_lang=detected_lang,

#                     history=history,

#                     summary_memory=summary_memory,

#                     structured_profile=structured_profile,

#                     conversation_state=conversation_state
#                 )

#                 agent_outputs[
#                     "symptom_analysis"
#                 ] = symptom_result

#             # ─────────────────────────────────
#             # RAG AGENT
#             # ─────────────────────────────────

#             elif tool == "vaccination_rag":

#                 rag_result = self.rag_agent.answer(
#                     english_text
#                 )

#                 agent_outputs[
#                     "medical_knowledge"
#                 ] = rag_result

#             # ─────────────────────────────────
#             # EDUCATION AGENT
#             # ─────────────────────────────────

#             elif tool == "disease_education":

#                 education_result = self._handle_education(

#                     english_text,

#                     name,

#                     history
#                 )

#                 agent_outputs[
#                     "education"
#                 ] = education_result

#             # ─────────────────────────────────
#             # OUTBREAK AGENT
#             # ─────────────────────────────────

#             elif tool == "outbreak_check":

#                 outbreak_result = self.outbreak_agent.check_area_outbreaks(

#                     pincode,

#                     detected_lang
#                 )

#                 if outbreak_result:

#                     agent_outputs[
#                         "outbreak_alert"
#                     ] = outbreak_result

#         # ─────────────────────────────────────
#         # FALLBACK
#         # ─────────────────────────────────────

#         if not agent_outputs:

#             fallback_result = self._handle_symptom(

#                 english_text=english_text,

#                 phone_number=phone_number,

#                 name=name,

#                 age=age,

#                 gender=gender,

#                 pincode=pincode,

#                 location_area=location_area,

#                 detected_lang=detected_lang,

#                 history=history,

#                 summary_memory=summary_memory,

#                 structured_profile=structured_profile,

#                 conversation_state=conversation_state
#             )

#             agent_outputs[
#                 "fallback_symptom_analysis"
#             ] = fallback_result

#         # ─────────────────────────────────────
#         # FINAL SYNTHESIS
#         # ─────────────────────────────────────

#         response_english = self.synthesis_agent.synthesize(

#             english_text,

#             agent_outputs
#         )

#         # ─────────────────────────────────────
#         # TRANSLATION
#         # ─────────────────────────────────────

#         final = self.language_agent.translate_response(

#             response_english,

#             detected_lang,

#             response_style
#         )

#         final_response = outbreak_prefix + final

#         # ─────────────────────────────────────
#         # SAVE ASSISTANT RESPONSE
#         # ─────────────────────────────────────

#         if conversation_id:

#             save_message(
#                 conversation_id,
#                 "assistant",
#                 final_response
#             )

#         # ─────────────────────────────────────
#         # VECTOR MEMORY STORAGE
#         # ─────────────────────────────────────

#         try:

#             memory_text = f"""
#                 User Query:
#                 {english_text}

#                 Assistant Response:
#                 {final_response}
#                 """

#             self.vector_memory.add_memory(

#                 memory_text,

#                 metadata={

#                     "phone_number": phone_number
#                 }
#             )

#             profile = self.profile_memory_agent.extract_profile(
#                 memory_text
#             )

#             self.memory_manager.save_medical_profile(

#                 phone_number,

#                 profile
#             )

#         except Exception as e:

#             logger.error(
#                 f"Vector memory save failed: {str(e)}"
#             )

#         # ─────────────────────────────────────
#         # AUTO MEMORY SUMMARIZATION
#         # ─────────────────────────────────────

#         try:

#             if conversation_id:

#                 recent_msgs = self.memory_manager.get_recent_messages(
#                     conversation_id,
#                     limit=20
#                 )

#                 if len(recent_msgs) >= 20:

#                     summary = self.memory_agent.summarize_conversation(
#                         recent_msgs
#                     )

#                     self.memory_manager.save_summary(
#                         conversation_id,
#                         summary
#                     )

#                     logger.info(
#                         f"Conversation summary updated "
#                         f"for conversation {conversation_id}"
#                     )

#         except Exception as e:

#             logger.error(
#                 f"Memory summarization failed: {str(e)}"
#             )

#         return final_response

#     # ═══════════════════════════════════════════
#     # USER STATE
#     # ═══════════════════════════════════════════

#     def _get_user_state(self, phone_number: str) -> dict:

#         if phone_number not in self.conversation_state:

#             self.conversation_state[phone_number] = {
#                 "active_topic": "",
#                 "task": "symptom_assessment",
#                 "stage": "detail_collection",
#                 "state": "NEW_TOPIC",
#                 "continue_context": True,
#                 "is_answer_to_question": False,
#                 "last_assistant_question": "",
#                 "pending_question": {
#                     "id": "",
#                     "slot": "",
#                     "question": ""
#                 },
#                 "slots": {},
#                 "pending_slots": [],
#                 "next_action": "continue_assessment",
#                 "note": "",
#                 "active_symptoms": [],
#                 "possible_conditions": [],
#                 "last_intent": "",
#                 "risk_level": "",
#                 "vaccination_context": {},
#             }

#         return self.conversation_state[phone_number]

#     def _get_last_assistant_message(
#         self,
#         history: list,
#         conversation_state: dict
#     ) -> str:

#         if history:
#             for msg in reversed(history):
#                 if msg["role"] == "assistant":
#                     return msg["content"]

#         return conversation_state.get("last_assistant_question", "")

#     # ═══════════════════════════════════════════
#     # SYMPTOM HANDLER
#     # ═══════════════════════════════════════════

#     def _handle_symptom(
#         self,
#         english_text,
#         phone_number,
#         name,
#         age,
#         gender,
#         pincode,
#         location_area,
#         detected_lang,
#         history,
#         summary_memory="",
#         structured_profile="",
#         conversation_state=None
#     ) -> str:

#         from tools.context_memory_tool import (
#             build_medical_context
#         )

#         medical_context = build_medical_context(
#             history
#         )

#         # ─────────────────────────────────────
#         # VECTOR MEMORY RETRIEVAL
#         # ─────────────────────────────────────

#         similar_memories = self.vector_memory.search_memory(

#             english_text,

#             k=5
#         )

#         ranked_memories = self.memory_selector_agent.rank_memories(

#             english_text,

#             similar_memories,

#             top_k=3
#         )

#         vector_context = "\n".join([

#             m["text"]

#             for m in ranked_memories
#         ])

#         # ─────────────────────────────────────
#         # AI ANALYSIS
#         # ─────────────────────────────────────

#         result = self.symptom_agent.analyze(

#             symptoms_english=english_text,

#             phone_number=phone_number,

#             user_name=name,

#             age=age,

#             gender=gender,

#             conversation_history=history,

#             medical_context=medical_context,

#             summary_memory=summary_memory,

#             vector_context=vector_context,

#             structured_profile=structured_profile,

#             conversation_state=conversation_state
#         )

#         # ─────────────────────────────────────
#         # REASONING
#         # ─────────────────────────────────────

#         reasoning = self.reasoning_agent.analyze_response(

#             english_text,

#             result
#         )

#         final_response = result["response"]

#         # FOLLOWUP

#         if reasoning.get("needs_followup"):

#             followup = reasoning.get(
#                 "followup_question",
#                 ""
#             )

#             if followup:

#                 final_response += (
#                     f"\n\n{followup}"
#                 )

#         # ─────────────────────────────────────
#         # SAVE CONSULTATION
#         # ─────────────────────────────────────

#         self.health_data_agent.save_consultation(

#             phone_number=phone_number,

#             symptoms=english_text,

#             possible_disease=result["possible_disease"],

#             advice=result["response"],

#             severity=result["severity"],

#             emergency=result["emergency"],

#             language_used=detected_lang
           
#         )

#         # ─────────────────────────────────────
#         # OUTBREAK DETECTION
#         # ─────────────────────────────────────

#         if result["possible_disease"] != "general illness":

#             outbreak_result = self.outbreak_agent.log_and_check(

#                 pincode=pincode,

#                 disease=result["possible_disease"],

#                 location_area=location_area,

#                 user_lang=detected_lang,
#             )

#             if (
#                 outbreak_result["is_outbreak"]
#                 and outbreak_result["alert_message"]
#             ):

#                 translated = self.language_agent.translate_response(

#                     outbreak_result["alert_message"],

#                     detected_lang
#                 )

#                 final_response += (
#                     f"\n\n⚠️ {translated}"
#                 )

#         final_response += self._smart_followup(
#             result
#         )

#         return final_response

#     # ═══════════════════════════════════════════
#     # EDUCATION
#     # ═══════════════════════════════════════════

#     def _handle_education(
#         self,
#         english_text: str,
#         name: str,
#         history: list
#     ) -> str:

#         txt = english_text.lower().strip()

#         if any(k in txt for k in VAGUE_EDUCATION) and len(txt.split()) < 5:

#             return (
#                 f"I'd love to teach you, {name}! 📚\n\n"
#                 f"Which disease or health topic would you like to know about?"
#             )

#         return self.education_agent.educate(
#             english_text,
#             name
#         )

#     # ═══════════════════════════════════════════
#     # FOLLOWUP
#     # ═══════════════════════════════════════════

#     def _smart_followup(self, result: dict) -> str:

#         if result["severity"] == "High":

#             return (
#                 "\n\n🔴 *This seems serious.* "
#                 "Please go to a doctor immediately."
#             )

#         elif result["severity"] == "Medium":

#             return (
#                 "\n\n💬 Are you experiencing any other symptoms?"
#             )

#         else:

#             return (
#                 "\n\n💬 Is there anything else you'd like to know?"
#             )

#     # ═══════════════════════════════════════════
#     # SPECIAL COMMANDS
#     # ═══════════════════════════════════════════

#     def _handle_special_commands(
#         self,
#         english_text,
#         name,
#         lang,
#         phone_number
#     ) -> str | None:

#         txt = english_text.lower().strip()

#         if any(k in txt for k in [
#             "my history",
#             "past records",
#             "health history"
#         ]):

#             return self.get_history_response(
#                 phone_number
#             )

#         if any(k in txt for k in [
#             "health tip",
#             "daily tip",
#             "tip"
#         ]):

#             tip = self.education_agent.daily_tip(
#                 name
#             )

#             return self.language_agent.translate_response(
#                 tip,
#                 lang
#             )

#         return None

#     # ═══════════════════════════════════════════
#     # HISTORY
#     # ═══════════════════════════════════════════

#     def get_history_response(
#         self,
#         phone_number: str,
#         response_style: str = "english"
#     ) -> str:

#         user = get_user(phone_number)

#         if not user:
#             return "❌ User not found."

#         lang = user["language"]

#         result = self.health_data_agent.get_history(
#             phone_number
#         )

#         return self.language_agent.translate_response(
#             result["formatted_summary"],
#             lang,
#             response_style
#         )