from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

import os
from dotenv import load_dotenv

load_dotenv()

class MedicalAgent:
    def __init__(self):
        self.model = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.1-8b-instant",
            temperature=0.3
        )


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
