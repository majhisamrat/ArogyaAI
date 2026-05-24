from tools.rag_tool import rag_medical_response


class RAGAgent:

    def __init__(self):
        self.name = "RAGAgent"

    def answer(self, query: str):

        return rag_medical_response(query)