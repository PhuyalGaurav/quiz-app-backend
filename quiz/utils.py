import openai
import qrcode
import base64
import json
import logging
import uuid
import io
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def process_image_with_openai(image_path):
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        if not settings.OPENAI_API_KEY:
            logger.error("OpenAI API key is not set")
            return {"error": "OpenAI API key is not configured"}
        
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        prompt = """
        Extract multiple-choice questions (MCQ) from this image. For each question:
        1. Extract the question text.
        2. Extract all answer choices.
        3. Identify which choice is the correct answer (if indicated in the image).
        
        Format the output as JSON with this structure:
        {
            "questions": [
                {
                    "question_text": "The question text here",
                    "choices": [
                        {"choice_text": "Option A", "is_correct": false},
                        {"choice_text": "Option B", "is_correct": true},
                        {"choice_text": "Option C", "is_correct": false},
                        {"choice_text": "Option D", "is_correct": false}
                    ]
                }
            ]
        }
        
        If the correct answer is not marked in the image, make all "is_correct" values false.
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        
        # Extract and parse the JSON response
        content = response.choices[0].message.content.strip()
        
        # Find the JSON part in the response
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start != -1 and json_end != -1:
            json_content = content[json_start:json_end]
            parsed_data = json.loads(json_content)
            return parsed_data
        else:
            logger.error("Failed to extract valid JSON from OpenAI response")
            return {"error": "No valid JSON found in the response"}
            
    except Exception as e:
        logger.error(f"Error processing image with OpenAI: {str(e)}")
        return {"error": str(e)}


def create_quiz_from_parsed_data(user, title, parsed_data, duration_minutes=10, is_public=False):
    """
    Create a quiz from parsed data returned by OpenAI.
    """
    from .models import Quiz, Question, Choice
    
    try:
        # Create a new Quiz
        quiz = Quiz.objects.create(
            title=title,
            creator=user,
            duration_minutes=duration_minutes,
            is_public=is_public,
            share_code=str(uuid.uuid4())[:8]
        )
        
        # Extract questions from parsed data
        questions_data = parsed_data.get('questions', [])
        
        for order, q_data in enumerate(questions_data):
            # Create Question
            question = Question.objects.create(
                quiz=quiz,
                text=q_data['question_text'],
                order=order
            )
            
            # Create Choices
            for choice_order, choice_data in enumerate(q_data.get('choices', [])):
                Choice.objects.create(
                    question=question,
                    text=choice_data['choice_text'],
                    is_correct=choice_data.get('is_correct', False),
                    order=choice_order
                )
                
        return quiz
    
    except Exception as e:
        logger.error(f"Error creating quiz from parsed data: {str(e)}")
        return None


def calculate_quiz_score(session):
    """
    Calculate the score for a quiz session.
    Returns a percentage score (0-100).
    """
    from .models import UserAnswer
    
    # Get total number of questions in the quiz
    total_questions = session.quiz.questions.count()
    
    if total_questions == 0:
        return 0
    
    # Get number of correct answers
    correct_answers = session.answers.filter(selected_choice__is_correct=True).count()
    
    # Calculate percentage score
    score = (correct_answers / total_questions) * 100
    return score


def complete_quiz_session(session):
    """
    Complete a quiz session, calculate the score, and save.
    """
    if not session.completed_at:
        session.completed_at = timezone.now()
        session.score = calculate_quiz_score(session)
        session.save()
    
    return session


def generate_qr_code(url, size=200, box_size=10):
    """
    Generate a QR code for a given URL and return as a base64 encoded string
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert the image to a base64 string
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return None
