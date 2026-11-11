import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_job_description(job_text: str):
    prompt = f"""
    You are an expert HR and AI Job Analyst. 
    Analyze the following Job Description and extract structured information in JSON format with these exact keys:
    - "job_title": Extract or infer the main role name.
    - "required_skills": List of technical and soft skills needed.
    - "experience_level": Junior, Mid, Senior, or Not Specified.
    - "key_responsibilities": List of main duties.
    - "summary": A brief 2-sentence overview of the role.

    Return ONLY valid JSON without markdown tags or extra text.

    Job Description:
    {job_text}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    clean_text = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(clean_text)

if __name__ == "__main__":
    sample_jd = """
    We are looking for a Python Developer with 3+ years of experience in FastAPI and PostgreSQL. 
    Responsibilities include building REST APIs, writing unit tests, and optimizing database queries.
    Knowledge of Git and Docker is a plus.
    """
    print("Analyzing Job Description...\n")
    result = analyze_job_description(sample_jd)
    print(json.dumps(result, indent=2))