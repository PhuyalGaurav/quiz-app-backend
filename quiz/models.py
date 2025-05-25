from django.db import models
from django.contrib.auth.models import User
import uuid
import json

class Quiz(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_quizzes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    duration_minutes = models.PositiveIntegerField(default=10)
    is_public = models.BooleanField(default=False)
    share_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    shared_with = models.ManyToManyField(
        User, 
        related_name='shared_quizzes', 
        blank=True,
        through='QuizShare',
        through_fields=('quiz', 'shared_with')
    )
    allow_anonymous_attempts = models.BooleanField(default=False, help_text="Allow users without an account to take this quiz")
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.share_code:
            self.share_code = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)
        
    def get_share_link(self):
        from django.conf import settings
        return f"{settings.FRONTEND_URL}/quiz/{self.share_code}" if hasattr(settings, 'FRONTEND_URL') else self.share_code


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.quiz.title} - Question {self.order + 1}"


class Choice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text


class ImageUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_images')
    image = models.ImageField(upload_to='quiz_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    parsed_data = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return f"Image by {self.user.username} ({self.uploaded_at})"
    
    def get_parsed_questions(self):
        if self.parsed_data:
            return json.loads(self.parsed_data) if isinstance(self.parsed_data, str) else self.parsed_data
        return None


class QuizSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    
    @property
    def is_completed(self):
        return self.completed_at is not None
    
    @property
    def is_timed_out(self):
        from django.utils import timezone
        if not self.completed_at:
            time_elapsed = timezone.now() - self.started_at
            return time_elapsed.total_seconds() > (self.quiz.duration_minutes * 60)
        return False

    def __str__(self):
        status = "Completed" if self.is_completed else "In Progress"
        return f"{self.user.username}'s attempt on {self.quiz.title} - {status}"


class UserAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'question']
    
    def __str__(self):
        return f"Answer to {self.question} by {self.session.user.username}"
        
    @property
    def is_correct(self):
        return self.selected_choice.is_correct


class QuizShare(models.Model):
    """Model to track quiz sharing between users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares_sent')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares_received')
    shared_at = models.DateTimeField(auto_now_add=True)
    permission_type = models.CharField(
        max_length=20,
        choices=[
            ('view', 'Can View'),
            ('attempt', 'Can Attempt'),
            ('edit', 'Can Edit'),
        ],
        default='attempt'
    )
    
    class Meta:
        unique_together = ['quiz', 'shared_with']
        
    def __str__(self):
        return f"{self.quiz.title} shared with {self.shared_with.username} by {self.shared_by.username}"
