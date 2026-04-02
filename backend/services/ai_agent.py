import json
import os
import requests
from google.genai import types
from datetime import datetime
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

class UnifiedLLMClient:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        self.gemini_client = genai.Client(api_key=self.gemini_key) if self.gemini_key else None
        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None

    def _call_gemini(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        if not self.gemini_client: return None
        try:
            response = self.gemini_client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None
            )
            return response.text if response.text else None
        except Exception as e:
            print(f"Gemini failed: {e}")
            return None

    def _call_groq(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        if not self.groq_client: return None
        # Using more reliable models for JSON tasks
        for model in ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]:
            try:
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                completion = self.groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    timeout=10.0
                )
                if completion.choices[0].message.content:
                    return completion.choices[0].message.content
            except Exception as e:
                print(f"Groq ({model}) failed: {e}")
        return None

    def _call_openrouter(self, prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
        if not self.openrouter_key: return None
        for model in ["google/gemini-flash-1.5", "meta-llama/llama-3.1-8b-instruct:free", "mistralai/mistral-7b-instruct:free"]:
            try:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                }
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                payload = {"model": model, "messages": messages}
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions", 
                    headers=headers, json=payload, timeout=15.0
                )
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
            except Exception as e:
                print(f"OpenRouter ({model}) failed: {e}")
        return None

    def generate_content(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        # Cascade through providers
        for call_fn in [self._call_gemini, self._call_groq, self._call_openrouter]:
            response = call_fn(prompt, system_instruction)
            if response:
                return response
        return ""

    def _extract_json(self, text: str) -> Optional[str]:
        if not text: return None
        import re
        # Try markdown block first
        code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if code_block:
            return code_block.group(1).strip()
            
        # Try finding the outermost brackets/curlies
        start_curly = text.find('{')
        end_curly = text.rfind('}')
        start_bracket = text.find('[')
        end_bracket = text.rfind(']')
        
        if start_curly != -1 and end_curly != -1 and (start_bracket == -1 or start_curly < start_bracket):
            return text[start_curly:end_curly+1]
        elif start_bracket != -1 and end_bracket != -1:
            return text[start_bracket:end_bracket+1]
        return text.strip()

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Any:
        format_instruction = "\nIMPORTANT: Respond ONLY with a valid JSON. No markdown backticks, no wrap-up text."
        full_prompt = prompt + format_instruction
        
        # Try each provider; if the provider fails OR returns invalid JSON, move to the next
        for provider_name, call_fn in [("Gemini", self._call_gemini), ("Groq", self._call_groq), ("OpenRouter", self._call_openrouter)]:
            response_text = call_fn(full_prompt, system_instruction)
            if not response_text:
                continue
                
            json_str = self._extract_json(response_text)
            if not json_str:
                continue
                
            try:
                data = json.loads(json_str)
                print(f"Successfully generated JSON using {provider_name}")
                return data
            except Exception as e:
                print(f"{provider_name} provided invalid JSON. Error: {e}. Retrying with next provider...")
                
        return None

llm = UnifiedLLMClient()

def _sanitize_description(desc: Any) -> str:
    """Force-converts any JSON-structured description into a formatted Markdown string."""
    if isinstance(desc, str):
        return desc
    if isinstance(desc, dict):
        lines = []
        for key, value in desc.items():
            k = key.replace("_", " ").title()
            if isinstance(value, list):
                lines.append(f"**{k}:**")
                for item in value:
                    lines.append(f"- {item}")
            else:
                lines.append(f"**{k}:** {value}")
        return "\n".join(lines)
    if isinstance(desc, list):
        return "\n".join([f"- {item}" for item in desc])
    return str(desc)

def generate_learning_plan(goal_title: str, daily_hours: float):
    # Dynamic duration extraction
    import re
    match = re.search(r"(\d+)\s*day", goal_title, re.IGNORECASE)
    duration = int(match.group(1)) if match else 5
    
    # Cap duration to prevent massive token usage, but allow more than 5
    duration = max(3, min(30, duration))

    prompt = f"""
    Create a highly detailed {duration}-day learning roadmap for the goal: '{goal_title}'.
    The user can study {daily_hours} hours daily.
    
    1. AUTOMATIC CORRECTION:
       First, identify if the goal title has any obvious typos (e.g., 'jaba' -> 'Java', 'pythun' -> 'Python').
       Provide the correct, professional technical title for the roadmap in 'corrected_title'.
    
    2. TASKS:
       Each task's 'description' MUST be a single STRING containing Markdown.
       It should include:
       - Specific sub-topics to cover for Day X.
       - 2-3 specific hands-on exercises or mini-projects for that day.
       - Key concepts to memorize or practice.
       Do NOT return 'description' as an object/map. It must be a plain STRING.
    """
    system = f"""You are a World-Class Technical Mentor. Return ONLY a JSON object:
    {{
      "corrected_title": "string",
      "tasks": [
        {{ "day_number": int, "topic": "string", "description": "string" }},
        ...
      ]
    }}
    The tasks list must contain exactly {duration} day objects."""
    
    response = llm.generate_json(prompt, system)
    if not response or not isinstance(response, dict):
        print("Failed to generate learning plan. No AI model responded.")
        return None
        
    tasks = response.get("tasks", [])
    corrected_title = response.get("corrected_title", goal_title)
    
    if not tasks:
        return None
        
    for p in tasks:
        p["description"] = _sanitize_description(p.get("description", ""))
        
    return {"tasks": tasks, "corrected_title": corrected_title}

def generate_quiz(topic: str, description: str):
    prompt = f"""
    Generate a 5-question multiple choice quiz for the topic: '{topic}'.
    CONTEXT: {description}
    
    GUIDELINES:
    - Questions must be scenario-based (e.g., 'If you have X and want Y, which approach is best?').
    - Provide 4 diverse options for each question.
    - Ensure 'correct_answer' is EXACTLY one of the strings in the 'options' list. 
    - VERY IMPORTANT: THE 'correct_answer' MUST BE IDENTICAL TO ONE OF THE OPTIONS STRINGS. No extra text, no explanation.
    - Vary the difficulty from conceptual to practical application.
    """
    system = """You are a Technical Assessment Expert. 
    Return ONLY a JSON object: 
    { 
      "questions": [
        {
          "question": "string", 
          "options": ["string", "string", "string", "string"], 
          "correct_answer": "string"
        }
      ] 
    }"""
    
    quiz = llm.generate_json(prompt, system)
    
    # Validation & Auto-schema wrapping
    if quiz:
        if isinstance(quiz, list) and len(quiz) > 0:
            return {"questions": quiz}
        if isinstance(quiz, dict) and "questions" in quiz and len(quiz["questions"]) > 0:
            return quiz
            
def identify_weak_topics(topic: str, description: str, missed_context: list):
    if not missed_context:
        return "None"
        
    prompt = f"""
    TOPIC: {topic}
    CONTEXT: {description}
    
    MISSED QUESTIONS & USER ANSWERS:
    {json.dumps(missed_context)}
    
    TASK: Based on the missed questions, identify exactly which 1-3 core concepts or sub-topics the student needs to revise. 
    Examples: 'Variable Scope', 'Recursion Base Case', 'Asynchronous Syntax'.
    
    CONSTRUCTION:
    Return a single STRING containing a comma-separated list of these topics. 
    Be specific and brief. No conversational filler.
    """
    system = "You are a Technical Tutor. Identify precise learning gaps from incorrect quiz answers."
    
    weak_areas_str = llm.generate_content(prompt, system)
    return weak_areas_str.strip() if weak_areas_str else "Further concept mastery needed"

def analyze_code(code: str, language: str, action: str, question: str = "", context_text: str = ""):
    action_prompt = {
        "debug": "Identify bugs and provide fixed versions.",
        "explain": "Explain this code clearly for a student.",
        "improve": "Analyze performance and suggest clean-code refactoring.",
        "solve_doubt": f"Answer this doubt accurately: {question}"
    }.get(action, "Analyze comprehensively.")
    
    prompt = f"""
    PERSONALIZED MENTORING SESSION:
    User Roadmap: {context_text}
    Current Topic/Question: {question}
    
    CODE CONTEXT ({language.upper()}):
    ``` {language}
    {code}
    ```
    
    YOUR TASK: {action_prompt}
    
    GUIDELINES:
    1. Specifically use idioms and best practices for {language} (e.g., Pythonic code, Modern C++, Rust safety, etc.).
    2. Reference the user's current roadmap progress ({context_text}) to tailor your explanation.
    3. If the code is a snippet, assume it's part of a larger project related to the goal.
    
    SPECIAL AGENTIC RULE:
    If the user expresses frustration, confusion, lack of confidence, or asks to revise a topic (e.g., 'I don't understand', 'I'm struggling'), 
    you MUST include the literal string '[REPLAN: TopicName]' in your response.
    
    Respond in Markdown as a Senior Software Engineer.
    """
    system = f"You are an expert {language} developer and Senior Mentor. Provide highly technical, encouraging, and accurate guidance using standard Markdown."
    
    response = llm.generate_content(prompt, system)
    if not response:
        return {"response": "I'm sorry, I couldn't reach my AI brain. Please try again in a moment.", "should_replan": False}
    
    import re
    replan_match = re.search(r"\[REPLAN:\s*(.*?)\]", response, re.IGNORECASE)
    should_replan = replan_match is not None
    replan_topic = replan_match.group(1).strip() if should_replan else None
    
    clean_response = re.sub(r"\[REPLAN:.*?\]", "", response, flags=re.IGNORECASE).strip()
    
    if not should_replan:
        frustration_keywords = ["don't understand", "not confident", "struggling", "confused", "hard", "difficult"]
        if any(kw in (question + code).lower() for kw in frustration_keywords):
            should_replan = True
            replan_topic = "this specific topic"
            
    return {
        "response": clean_response, 
        "should_replan": should_replan,
        "replan_topic": replan_topic
    }

def analyze_performance(quiz_results: list, all_tasks: list, days_since_start: int):
    # 1. Identify Technical Gaps (Weak Topics Box)
    failed_attempts = [q for q in quiz_results if q.score < 0.6]
    weak_topics = list(set([f.weak_areas for f in failed_attempts if f.weak_areas and f.weak_areas.lower() != "none"]))
    
    # 2. Analyze Pacing (Status Box)
    overdue_tasks = [t for t in all_tasks if not t.is_completed and t.day_number < days_since_start]
    
    status = "On Track"
    if len(overdue_tasks) > 2:
        status = "Behind Schedule"
    elif weak_topics:
        status = "Adjustment Recommended"
    elif len(all_tasks) > 0 and all(t.is_completed for t in all_tasks if t.day_number <= days_since_start):
        status = "On Track"
    
    # 3. Generate Personalized Mentor Tip (AI Recommendation Box)
    # We use a very fast, targeted prompt to the LLM
    prompt = f"""
    Context:
    - User Status: {status}
    - Weak Topics: {', '.join(weak_topics) if weak_topics else 'None identified'}
    - Tasks Overdue: {len(overdue_tasks)}
    - Goal: {all_tasks[0].goal.title if all_tasks else 'Learning'}
    
    Task: Provide a 1-sentence, high-impact, encouraging mentor tip for the dashboard. 
    Focus on motivation or a specific technical study tip. Keep it under 20 words.
    """
    system = "You are an elite Technical Coach. Be brief, professional, and highly encouraging."
    
    # Use generate_content for a simple string response
    recommendation = llm.generate_content(prompt, system)
    
    if not recommendation:
        # Fallback if AI is down
        if status == "Behind Schedule":
            recommendation = "You've got some catching up to do. Focus on one task at a time!"
        elif status == "Adjustment Recommended":
            recommendation = "Mastering the basics now will save you weeks later. Review your weak areas."
        else:
            recommendation = "Great consistency! Keep pushing, you're doing amazing."

    return {
        "status": status,
        "recommendation": recommendation.strip(),
        "weak_topics": weak_topics if weak_topics else ["Zero weak areas detected! Keep it up."],
        "overdue_count": len(overdue_tasks)
    }

def replan_roadmap(goal_title: str, remaining_days: list, weak_topics: list, reason: str):
    prompt = f"""
    GOAL: {goal_title}
    REASON FOR ADJUSTMENT: {reason}
    WEAK AREAS: {', '.join(weak_topics)}
    
    CURRENT REMAINING SCHEDULE:
    {json.dumps(remaining_days)}
    
    YOUR TASK: 
    1. Merge a revision of the weak areas into the VERY NEXT task in the list.
    2. Update that task's description to include a focus on these revision topics while preserving the original learning goals.
    3. Return the FULL updated list of ALL remaining tasks provided in the 'CURRENT REMAINING SCHEDULE'.
    4. Do NOT remove or skip any future days. Every day number from the input must be present in the output.
    5. Maintain the chronological order of day numbers.
    6. Ensure the output is a valid JSON array of objects.
    
    Format: [ {{ "day_number": int, "topic": "string", "description": "string" }}, ... ]
    """
    system = "You are a Senior Learning Architect. You MUST return a complete JSON array containing the revised schedule."
    
    new_plan = llm.generate_json(prompt, system)
    if not new_plan or not isinstance(new_plan, list):
        return remaining_days
        
    for p in new_plan:
        p["description"] = _sanitize_description(p.get("description", ""))
        
    return new_plan
