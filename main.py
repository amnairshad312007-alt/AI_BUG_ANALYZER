from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Job Description Analyzer API")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class JobRequest(BaseModel):
    job_text: str

@app.post("/analyze")
def analyze_job(request: JobRequest):
    try:
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
        {request.job_text}
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        clean_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))