from Prompt.Identity import get_context, get_identity_prompt, get_rules, get_instructions_prompt, get_examples_prompt, set_question_context
from typing import Optional


class Prompt:
    def __init__(self, assessment_build: Optional[dict], questions: Optional[dict], student_response: Optional[str]): 
        self.assessment_build: Optional[dict] = assessment_build
        self.questions = questions
        self.prompt = None
        self.student_response = student_response
        self.prompt = self.build_prompt()
            

    def build_prompt(self)-> str:
        return (
            get_identity_prompt()
            + get_instructions_prompt()
            + get_context(self.assessment_build.get("title"), self.assessment_build.get("description"), self.assessment_build.get("subject_title"), self.assessment_build.get("max_score"))
            + get_rules()
            + set_question_context(self.questions.get("question_text"), self.questions.get("answer_text"), self.questions.get("points"), self.student_response)
            + get_examples_prompt()
        )

    def get_prompt(self) ->str:
        return self.prompt

    def get_token_length(self) ->int:
        compressed = "".join(self.prompt.split())
        return (len(compressed) + 2) // 3

    def get_input_length(self) ->int:
        compressed = "".join(self.prompt.split())
        return (len(compressed) + 2) // 3
    
    