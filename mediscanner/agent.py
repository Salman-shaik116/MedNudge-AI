from langchain_core.prompts import PromptTemplate

import os
from dotenv import load_dotenv

from .llm import create_chat_model

load_dotenv()

class MedicalAgent:
    def __init__(self):
        self.model = create_chat_model(temperature=0.3)


    def analyze(self, text):
        prompt = PromptTemplate(
            input_variables=["report"],
            template="""
            Analyze the medical report and provide:
            - Summary
            - Possible conditions
            - Tablets & Medications for a reference
            - Food & Diet in a week 
            - Exercises for a week
            - what to avoid

            Report:
            {report}
            """
        )
        chain = prompt | self.model
        response = chain.invoke({"report": text})
        return response.content
