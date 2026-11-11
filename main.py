<<<<<<< HEAD
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
=======
import os
from typing import TypedDict, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable missing!")

# Initialize Gemini Model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=api_key,
    temperature=0.2
)

# Define State Structure for LangGraph
class BugReportState(TypedDict):
    user_input: str
    title: str
    feature: str
    summary: str
    severity: str
    possible_causes: List[str]
    final_report: str

# -------------------------------------------------------------------
# LangGraph Nodes
# -------------------------------------------------------------------

def node_bug_analysis(state: BugReportState) -> dict:
    """Node 1: Extract bug title, affected feature, and issue summary."""
    prompt = f"""
    Analyze the following raw bug description:
    "{state['user_input']}"

    Extract the following details:
    1. A concise Bug Title
    2. The Affected Feature/Component
    3. A clear Issue Summary (2-3 sentences)

    Format your output strictly as:
    Title: <title>
    Feature: <feature>
    Summary: <summary>
    """
    response = llm.invoke(prompt).content.strip()
    
    title, feature, summary = "Unknown", "Unknown", "Unknown"
    for line in response.split("\n"):
        if line.startswith("Title:"):
            title = line.replace("Title:", "").strip()
        elif line.startswith("Feature:"):
            feature = line.replace("Feature:", "").strip()
        elif line.startswith("Summary:"):
            summary = line.replace("Summary:", "").strip()

    return {"title": title, "feature": feature, "summary": summary}

def node_severity_detection(state: BugReportState) -> dict:
    """Node 2: Classify severity level (Critical, High, Medium, Low)."""
    prompt = f"""
    Based on this bug summary:
    Title: {state['title']}
    Feature: {state['feature']}
    Summary: {state['summary']}

    Determine the severity level of this bug. Choose EXACTLY ONE from:
    - Critical (App crash, data loss, security vulnerability, blocking all users)
    - High (Major feature broken, no easy workaround)
    - Medium (Minor feature broken, workaround available)
    - Low (Cosmetic issue, typo, minor visual glitch)

    Return ONLY the severity label (Critical, High, Medium, or Low) followed by a 1-sentence justification.
    Format: Severity: <Level> - <Justification>
    """
    response = llm.invoke(prompt).content.strip()
    return {"severity": response}

def node_root_cause(state: BugReportState) -> dict:
    """Node 3: Suggest possible root causes of the bug."""
    prompt = f"""
    Given the bug details:
    Title: {state['title']}
    Feature: {state['feature']}
    Summary: {state['summary']}
    Severity: {state['severity']}

    Suggest 3 realistic technical root causes or backend/frontend triggers for this bug.
    Provide them as a bulleted list.
    """
    response = llm.invoke(prompt).content.strip()
    causes = [c.strip("- ").strip() for c in response.split("\n") if c.strip()]
    return {"possible_causes": causes}

def node_format_report(state: BugReportState) -> dict:
    """Node 4: Compile structured, clean bug report."""
    causes_formatted = "\n".join([f"  • {cause}" for cause in state['possible_causes']])
    
    report = f"""==================================================
              STRUCTURED BUG REPORT
==================================================
📌 TITLE:
   {state['title']}

🧩 AFFECTED FEATURE:
   {state['feature']}

⚡ SEVERITY:
   {state['severity']}

📝 SUMMARY:
   {state['summary']}

🔍 POSSIBLE ROOT CAUSES:
{causes_formatted}
=================================================="""

    return {"final_report": report}

# -------------------------------------------------------------------
# Build LangGraph Workflow
# -------------------------------------------------------------------

workflow = StateGraph(BugReportState)

workflow.add_node("analyze_bug", node_bug_analysis)
workflow.add_node("detect_severity", node_severity_detection)
workflow.add_node("suggest_root_cause", node_root_cause)
workflow.add_node("format_report", node_format_report)

workflow.set_entry_point("analyze_bug")
workflow.add_edge("analyze_bug", "detect_severity")
workflow.add_edge("detect_severity", "suggest_root_cause")
workflow.add_edge("suggest_root_cause", "format_report")
workflow.add_edge("format_report", END)

app_graph = workflow.compile()

# -------------------------------------------------------------------
# FastAPI App & Endpoints
# -------------------------------------------------------------------

app = FastAPI(title="AI Bug Analyzer")

class BugInputRequest(BaseModel):
    description: str

@app.post("/analyze-bug")
async def analyze_bug_endpoint(request: BugInputRequest):
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Bug description cannot be empty.")
    
    initial_state = {
        "user_input": request.description,
        "title": "",
        "feature": "",
        "summary": "",
        "severity": "",
        "possible_causes": [],
        "final_report": ""
    }
    
    try:
        final_output = app_graph.invoke(initial_state)
        return {
            "title": final_output["title"],
            "feature": final_output["feature"],
            "severity": final_output["severity"],
            "summary": final_output["summary"],
            "possible_causes": final_output["possible_causes"],
            "formatted_report": final_output["final_report"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
>>>>>>> f8d36b49f3cce37aec03ce11c5994c60ce32b256
