from tools.symptom_tool import analyze_symptoms
from tools.health_record_tool import fetch_health_history
from tools.education_tool import get_disease_education
from tools.outbreak_tool import check_outbreak_in_area
from tools.rag_tool import rag_medical_response
from config.logger import logger



TOOL_REGISTRY = {
    "symptom_analysis": {
        "function": analyze_symptoms,
        "description": "Analyze patient symptoms and detect possible diseases"
    },

    "health_history": {
        "function": fetch_health_history,
        "description": "Fetch user's previous health consultation history"
    },

    "vaccination_rag": {
    "function": rag_medical_response,
    "description": "Answer vaccination and pregnancy questions using medical PDFs"
    },

    "disease_education": {
        "function": get_disease_education,
        "description": "Provide educational information about diseases"
    },

    "outbreak_check": {
        "function": check_outbreak_in_area,
        "description": "Check outbreaks in a pincode area"
    },
}