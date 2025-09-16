

def get_identity()->str:
    return f"""
        Identity: You are a materials generator. Materials are study guides, teaching guides, tutor guides. You will recieve context on a assessment to use as a model.
        The context provided is assessment title, max_score, subject, description. As well as the questions for the assessment in a list of objects.
        Your goal is to examine the assessment meta data, questions, and produce a guide in the form of a JSON string. This material will be used by educators
        to teach, tutor, mentor students for preparation for the assessment. 
    """

def get_instructions(title, subject, description, questions, bias_type: str)->str:
    return f"""
        Instructions: Generate a {bias_type} for assessment {title} whos subject is {subject}, with a description {description}.
        Generate an appropriate response by creating similar questions, examples with solutions, tips elaborate and explain why, etc.
        Questions => {questions}
    """

def get_restriction_output_start() ->str:
    return f"The response string MUST start with: ```json"

def get_restriction_output_end() ->str:
    return f"The response string MUST end with: ```"



def get_example()->str:
    return """
        Example response:
        ```json:
        {
            "guide_type": "study_guide | teacher_guide | session_guide",
            "subject": "Math | History | Biology | ...",
            "grade_level": "string",
            "duration_minutes": "integer",
            "learning_objectives": [
                "string"
            ],
            "key_concepts": [
                {
                "title": "string",
                "explanation": "string",
                "examples": ["string"]
                }
            ],
            "activities": [
                {
                "title": "string",
                "description": "string",
                "steps": ["string"],
                "expected_outcome": "string"
                }
            ],
            "assessment_questions": [
                {
                "question": "string",
                "answer": "string",
                "difficulty": "easy | medium | hard"
                }
            ],
            "summary": "string",
            "materials_needed": ["string"],
            "appendix": "string (optional)"
        }```
    """