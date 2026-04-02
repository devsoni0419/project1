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

    def generate_content(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        # Prio 1: Gemini (Highest Quality)
        if self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model='gemini-3-flash-preview', 
                    contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None
                )
                if response.text:
                    return response.text
            except Exception as e:
                print(f"Gemini 3 Flash failed: {e}")

        # Prio 2: Groq (Ultra Fast Fallback)
        if self.groq_client:
            for model in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192"]:
                try:
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": prompt})
                    
                    completion = self.groq_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        timeout=8.0 # Aggressive failover for speed
                    )
                    if completion.choices[0].message.content:
                        return completion.choices[0].message.content
                except Exception as e:
                    print(f"Groq model {model} failed: {e}")

        # Prio 3: OpenRouter (Deep Backup)
        if self.openrouter_key:
            for model in ["meta-llama/llama-3.1-8b-instruct:free", "mistralai/mistral-7b-instruct:free"]:
                try:
                    headers = {
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                    }
                    messages = []
                    if system_instruction:
                        messages.append({"role": "system", "content": system_instruction})
                    messages.append({"role": "user", "content": prompt})
                    
                    payload = {
                        "model": model,
                        "messages": messages
                    }
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions", 
                        headers=headers, 
                        json=payload,
                        timeout=12.0
                    )
                    if response.status_code == 200:
                        return response.json()['choices'][0]['message']['content']
                except Exception as e:
                    print(f"OpenRouter model {model} failed: {e}")

        return ""

    def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Any:
        full_prompt = prompt + "\nRespond ONLY with a valid JSON object or array. No markdown, no triple backticks."
        response_text = self.generate_content(full_prompt, system_instruction)
        
        if not response_text:
            return None
            
        cleaned = response_text.strip()
        
        # 1. Handle Markdown Blocks: ```json ... ```
        import re
        code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if code_block:
            json_str = code_block.group(1).strip()
        else:
            # 2. Extract outermost JSON structure
            start_curly = cleaned.find('{')
            end_curly = cleaned.rfind('}')
            start_bracket = cleaned.find('[')
            end_bracket = cleaned.rfind(']')
            
            has_obj = start_curly != -1 and end_curly != -1
            has_arr = start_bracket != -1 and end_bracket != -1
            
            if has_obj and has_arr:
                if start_curly < start_bracket:
                    json_str = cleaned[start_curly:end_curly+1]
                else:
                    json_str = cleaned[start_bracket:end_bracket+1]
            elif has_obj:
                json_str = cleaned[start_curly:end_curly+1]
            elif has_arr:
                json_str = cleaned[start_bracket:end_bracket+1]
            else:
                json_str = cleaned

        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"JSON Parse Error: {e}\nRaw content excerpt: {response_text[:400]}...")
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
    
    CRITICAL RULE:
    Each task's 'description' MUST be a single STRING containing Markdown.
    It should include:
    - Specific sub-topics to cover for Day X.
    - 2-3 specific hands-on exercises or mini-projects for that day.
    - Key concepts to memorize or practice.
    Do NOT return 'description' as an object/map. It must be a plain STRING.
    """
    system = f"You are a World-Class Technical Mentor. Return a JSON array of exactly {duration} task objects. Keys: day_number (int), topic (string), description (string)."
    
    plan = llm.generate_json(prompt, system)
    if not plan or not isinstance(plan, list):
        print("Failed to generate learning plan. No AI model responded.")
        return None
        
    for p in plan:
        p["description"] = _sanitize_description(p.get("description", ""))
    return plan

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
            
    print(f"Quiz Generation Failed for topic '{topic}'.")
    return None

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
    Code Provided ({language}):
    {code}
    
    TASK: {action_prompt}
    
    SPECIAL AGENTIC RULE:
    If the user expresses frustration, confusion, lack of confidence, or asks to revise a topic (e.g., 'I don't understand Time Complexity', 'I'm struggling'), 
    you MUST include the literal string '[REPLAN: TopicName]' in your response (either at the start or end).
    This string is a machine-readable instruction to rebuild their roadmap.
    
    Respond in Markdown as a Senior Software Engineer.
    """
    system = "You are a Senior Software Engineer and Mentor. Be encouraging and technical. Use Markdown."
    
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
    failed_attempts = [q for q in quiz_results if q.score < 0.6]
    weak_topics = list(set([f.weak_areas for f in failed_attempts if f.weak_areas and f.weak_areas.lower() != "none"]))
    
    overdue_tasks = [t for t in all_tasks if not t.is_completed and t.day_number < days_since_start]
    
    recommendation = "You're on the right track! Focus on maintaining daily consistency."
    status = "On Track"
    
    if weak_topics:
        status = "Adjustment Recommended"
        recommendation = f"It looks like you're struggling with {', '.join(weak_topics)}. I recommend a deeper dive into these fundamentals before moving on."
    
    if len(overdue_tasks) > 2:
        status = "Behind Schedule"
        recommendation = "You have several pending tasks from previous days. Consider re-balancing your roadmap to stay achievable."

    return {
        "status": status,
        "recommendation": recommendation,
        "weak_topics": weak_topics,
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
