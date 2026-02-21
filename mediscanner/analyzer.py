from .agent import MedicalAgent
from .config import GROQ_API_KEY
from mediscanner.file_extractor import extract_text
def analyze_medical_report(file):
    text = extract_text(file)
    agent = MedicalAgent()
    return agent.analyze(text)
