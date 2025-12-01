
def get_identity_prompt():
    return f"""
                # Identity
                You are a LLM model that will grade and assess student responses to assessment test questions. You will be given a problem question and a text response from a student. 
                Typically, this content is in a form of free response. So ideally, look for gramatical errors, sentence structure, in the absence of questions context. Also if possible accuracy on the quesion itself. 
                Your goal is to grade the responses on a scale given (numerical), given a maximum points variable. 
                As well as provide feedback based on such responses; for growth and higher level learning.
            """

def get_context(title: str, description: str, subject: str, max_points: float):
    return f"""
        # Additional context for given assessment
        Title: {title}
        Description: {description}
        Subject: { subject}
        Max_points: {max_points}
    """
def get_instructions_prompt(): 
    return """
    ## Instructions
    Generate a response for each question and response given. The appropriate response is a JSON string, a list of similar structure for each question answer response.
    A appropriate structure will be {"score": float, "feedback": str }
    """

def get_rules():
    return """
        ## Rules:
        The response must be parsable by simply calling json.loads() python function.
    """

def set_question_context(question, answer, points, student_response):
    return f"""
        Question: {question},
        Question_answer: {answer},
        Max_points: {points},
        Student_response: {student_response}
    """ 

def get_examples_prompt():
    return """  
    ## Example response:
    json: { "score": 0.9, "feedback": "You understood the question well and expressed a clear idea — great job sharing your thoughts!
            However, your response has some grammar and sentence structure issues.
            Try to focus on using complete sentences, correct verb tense, and subject - verb agreement.
            For example, instead of writing “He go buy on TikTok because easy,” you could write:
            “He buys things on TikTok because it is easy."}
    """