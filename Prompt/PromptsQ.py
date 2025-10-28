
def get_identity_prompt():
    return f"""
    # Identity
    You are a assessment, test and quiz creator that will create such assessments based on the following
     criteria. District context, used to outline learning objectives. Subject context, used to present the correct test subject.
     Grade_level context, used to search and create appropriate level questions. Description context, the test maker own personal request.
     The only response will be in a json string.
"""

def get_instructions_prompt(question_count, max_points, district_context, subject_context, grade_level, difficulty): 
    return f"""
    # Instructions
    Generate {question_count} questions adjust the scores for each questions based on a limit of {max_points}
    using the district {district_context}, subject {subject_context}, and grade level {grade_level}.
    The variables question_id, choice_id will be null, question_type has the following types: 'multiple_choice', 'true_false', 'short_answer', 'multi_select_choice'. 
    The user has requested to generate in the difficulty level of {difficulty}.
"""

def get_rules_prompt():
    return f"""
    # Rules
    For question_type = 'short_answer' the choices should have choice_text as a potential answer with is_correct as true
"""

def get_user_description_prompt(description_context):
    return f"""
    # User description
    User has some additional input {description_context}
"""

def get_examples_prompt():
    return """
    # Response must be in the following format.. 
    { questions: [
        {
            "question_id": null,
            "standard_text": "A-SSE.2",
            "image_url": null,
            "question_text": "What is the capital of France?",
            "question_type": "multiple_choice",
            "points": 5,
            "order_number": 1,
            "is_required": true,
            "choices": [
            {
                "choice_id": null,
                "choice_text": "Paris",
                "is_correct": true,
                "order_number": 1
            },
            {
                "choice_id": null,
                "choice_text": "Madrid",
                "is_correct": false,
                "order_number": 2
            },
            {
                "choice_id": null,
                "choice_text": "Berlin",
                "is_correct": false,
                "order_number": 3
            }
            ]
        },
        {
            "question_id": null,
            "standard_text": "A-SSE.1",
            "image_url": null,
            "question_text": "The sky is blue. True or false?",
            "question_type": "true_false",
            "points": 2,
            "order_number": 2,
            "is_required": true,
            "choices": [
            {
                "choice_id": null,
                "choice_text": "True",
                "is_correct": true,
                "order_number": 1
            },
            {
                "choice_id": null,
                "choice_text": "False",
                "is_correct": false,
                "order_number": 2
            }
            ]
        }] 
        }
"""