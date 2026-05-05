import os
import json
from openai import OpenAI
from dotenv import load_dotenv

class AIHandler:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("AI_API_KEY")
        self.base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")
        
        if not self.api_key:
            raise ValueError("AI_API_KEY not found in environment variables.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.profile = None

    def generate_completion(self, system_prompt, user_prompt, json_mode=False):
        """Generic method to get AI completions."""
        try:
            response_format = {"type": "json_object"} if json_mode else {"type": "text"}
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=response_format
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling AI: {e}")
            return None

    def extract_profile(self, resume_path="assests/resume.txt"):
        """Reads resume and extracts structured profile data."""
        if not os.path.exists(resume_path):
            print(f"Resume file not found at {resume_path}")
            return None

        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()

        system_prompt = (
            "You are an expert HR recruiter and profile analyzer. "
            "Your task is to extract key professional metrics from a resume and return them as a structured JSON object. "
            "Ensure accuracy, especially for years of experience and core skills."
        )
        
        user_prompt = (
            f"Resume Text:\n{resume_text}\n\n"
            "Extract the following fields in JSON format:\n"
            "- full_name\n"
            "- years_of_experience (as a number, e.g., 4.5)\n"
            "- skills (categorized: frontend, backend, ai_automation, tools)\n"
            "- current_location\n"
            "- preferred_locations (list)\n"
            "- current_ctc (if mentioned, otherwise null)\n"
            "- expected_ctc (if mentioned, otherwise null)\n"
            "- notice_period (string, e.g., 'Immediate Joiner', '0 days')\n"
            "- azure_experience (string/years if mentioned)\n"
            "- summary (2-sentence professional summary)"
        )

        print("Analyzing Resume...")
        response = self.generate_completion(system_prompt, user_prompt, json_mode=True)
        
        if response:
            try:
                self.profile = json.loads(response)
                return self.profile
            except json.JSONDecodeError:
                print("Failed to parse AI response as JSON.")
                return None
        return None

    def get_profile(self):
        """Returns the extracted profile, extracting it if not already done."""
        if not self.profile:
            return self.extract_profile()
        return self.profile

    def solve_questionnaire(self, job_title, job_description, questionnaire):
        """Uses AI to solve a job questionnaire based on the user's profile."""
        profile = self.get_profile()
        if not profile:
            print("Cannot solve questionnaire without a profile.")
            return {}

        system_prompt = (
            "You are an expert career assistant. Your task is to answer job application questionnaires "
            "on behalf of a candidate, using their professional profile as the source of truth. "
            "Maintain consistency and professionalism. Ensure all answers match the candidate's actual experience."
        )

        # Prepare questionnaire context for AI
        q_list = []
        for q in questionnaire:
            qid = q.get("questionId")
            qtext = q.get("questionName") or ""
            qtype = q.get("questionType")
            options = q.get("answerOption") or {}
            
            q_info = {
                "id": qid,
                "text": qtext,
                "type": qtype,
                "options": options
            }
            q_list.append(q_info)

        user_prompt = (
            f"Candidate Profile:\n{json.dumps(profile, indent=2)}\n\n"
            f"Job Title: {job_title}\n"
            f"Job Description: {job_description}\n\n"
            f"Questionnaire:\n{json.dumps(q_list, indent=2)}\n\n"
            "Answer each question in the questionnaire. For radio buttons/dropdowns, return the KEY of the best option. "
            "For text boxes, provide a concise, professional answer. "
            "Return a JSON object where keys are question IDs and values are the answers."
        )

        print(f"Solving questionnaire for '{job_title}'...")
        response = self.generate_completion(system_prompt, user_prompt, json_mode=True)

        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                print("Failed to parse AI questionnaire response.")
                return {}
        return {}
