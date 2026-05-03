import json
from src.utils.ai_handler import AIHandler

def test_questionnaire_solving():
    try:
        handler = AIHandler()
        # Ensure profile is loaded
        handler.extract_profile()
        
        mock_job_title = "Senior Software Developer (Angular & Node.js)"
        mock_jd = (
            "We are looking for a Senior Developer with experience in Angular, Node.js, and .NET Core. "
            "You should have at least 4 years of experience and be willing to work in Pune. "
            "Experience with AI automation is a plus."
        )
        
        mock_questionnaire = [
            {
                "questionId": "q1",
                "questionName": "What is your total experience in years?",
                "questionType": "Text Box"
            },
            {
                "questionId": "q2",
                "questionName": "Are you willing to work from Pune?",
                "questionType": "Radio Button",
                "answerOption": {
                    "1": "Yes",
                    "2": "No"
                }
            },
            {
                "questionId": "q3",
                "questionName": "What is your current notice period?",
                "questionType": "Text Box"
            },
            {
                "questionId": "q4",
                "questionName": "Have you ever worked with OpenAI API?",
                "questionType": "Radio Button",
                "answerOption": {
                    "yes": "Yes, extensive experience",
                    "no": "No"
                }
            }
        ]
        
        print("\n--- Starting Questionnaire Solving Test ---")
        answers = handler.solve_questionnaire(mock_job_title, mock_jd, mock_questionnaire)
        
        print("\nAI Generated Answers:")
        print(json.dumps(answers, indent=4))
        
        # Basic validation
        assert "q1" in answers, "Question 1 missing"
        assert "q2" in answers, "Question 2 missing"
        assert answers["q2"] == "1", f"Expected '1' for Pune willingness, got {answers['q2']}"
        
        print("\nTest Passed!")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_questionnaire_solving()
