from config.settings import (
    get_llm_response,
    GROQ_MAIN_MODEL
)

import json


class ProfileMemoryAgent:

    def extract_profile(
        self,
        conversation_text: str
    ) -> dict:

        messages = [

            {
                "role": "system",
                "content": (
                    "Extract structured medical memory "
                    "from the conversation.\n\n"

                    "Return ONLY valid JSON.\n\n"

                    "Format:\n"

                    "{\n"
                    '  "diseases": [],\n'
                    '  "allergies": [],\n'
                    '  "medications": [],\n'
                    '  "recurring_symptoms": []\n'
                    "}\n\n"

                    "Do not explain anything."
                )
            },

            {
                "role": "user",
                "content": conversation_text
            }
        ]

        response = get_llm_response(

            messages,

            model=GROQ_MAIN_MODEL,

            temperature=0.1,

            max_tokens=300
        )

        try:

            data = json.loads(response)

            return {

                "diseases":
                    data.get("diseases", []),

                "allergies":
                    data.get("allergies", []),

                "medications":
                    data.get("medications", []),

                "recurring_symptoms":
                    data.get(
                        "recurring_symptoms",
                        []
                    )
            }

        except:

            return {

                "diseases": [],
                "allergies": [],
                "medications": [],
                "recurring_symptoms": []
            }