from Prompt.Prompts import get_identity, get_instructions, get_example, get_restriction_output_start, get_restriction_output_end

class Prompt:
    def __init__(self, questions: str, title: str, description: str, max_score: int, subject: str, bias_type: str):
        self.questions = questions
        self.title = title
        self.description = description
        self.max_score = max_score
        self.subject = subject
        self.bias_type = bias_type
        self.prompt = self.build_prompt()
    

    def build_prompt(self)-> str:
        return (
            get_identity()
            + get_instructions(self.title,self.subject ,self.description, self.questions, self.bias_type)
            + get_example()
            + get_restriction_output_start()
            + get_restriction_output_end()
        )

    def get_prompt(self) ->str:
        return self.prompt

    def get_token_length(self) ->int:
        compressed = "".join(self.prompt.split())
        return (len(compressed) + 2) // 3
    
    