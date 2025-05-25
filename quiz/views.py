from django.shortcuts import render

from rest_framework import viewsets, status, generics, permissions, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils import timezone
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from .models import Quiz, Question, Choice, ImageUpload, QuizSession, UserAnswer, QuizShare
from .serializers import (
    UserSerializer, UserRegistrationSerializer, QuizSerializer, 
    QuizDetailSerializer, QuestionSerializer, ChoiceSerializer,
    ImageUploadSerializer, QuizSessionSerializer, UserAnswerSerializer,
    QuizSessionResultSerializer, QuizShareSerializer
)
from .utils import process_image_with_openai, create_quiz_from_parsed_data, complete_quiz_session


class IsCreatorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
            
        return obj.creator == request.user


class IsQuizCreatorOrParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.quiz.creator == request.user:
            return True
            
        if obj.user == request.user:
            return True
            
        return False


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
        

class QuizShareViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing quiz shares
    """
    serializer_class = QuizShareSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return QuizShare.objects.filter(
            # Shares created by this user OR shares received by this user
            models.Q(shared_by=self.request.user) | 
            models.Q(shared_with=self.request.user)
        )
    
    @action(detail=False, methods=['get'])
    def sent(self, request):
        """List shares sent by the current user"""
        shares = QuizShare.objects.filter(shared_by=request.user)
        serializer = self.get_serializer(shares, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def received(self, request):
        """List shares received by the current user"""
        shares = QuizShare.objects.filter(shared_with=request.user)
        serializer = self.get_serializer(shares, many=True)
        return Response(serializer.data)


class JoinQuizByShareCodeView(generics.RetrieveAPIView):
    """
    View to join a quiz using a share code, with optional automatic session creation
    """
    serializer_class = QuizDetailSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        share_code = self.kwargs.get('share_code')
        return get_object_or_404(Quiz, share_code=share_code)
    
    def retrieve(self, request, *args, **kwargs):
        quiz = self.get_object()
        
        # Check if the quiz is accessible
        if not quiz.is_public:
            if request.user.is_anonymous:
                if not quiz.allow_anonymous_attempts:
                    return Response(
                        {"error": "This quiz is private. Please log in to attempt it."}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif quiz.creator != request.user and not quiz.shared_with.filter(id=request.user.id).exists():
                return Response(
                    {"error": "You don't have access to this quiz."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get the quiz details
        serializer = self.get_serializer(quiz)
        data = serializer.data
        
        # If auto_start is set to true and user is authenticated, create a session
        if request.query_params.get('auto_start') == 'true' and not request.user.is_anonymous:
            # Check if there's an active session already
            existing_session = QuizSession.objects.filter(
                quiz=quiz, 
                user=request.user, 
                completed_at__isnull=True
            ).first()
            
            if existing_session and not existing_session.is_timed_out:
                # Return existing session
                session_data = QuizSessionSerializer(existing_session).data
                data['active_session'] = session_data
            else:
                # Create a new session
                session = QuizSession.objects.create(quiz=quiz, user=request.user)
                session_data = QuizSessionSerializer(session).data
                data['active_session'] = session_data
        
        return Response(data)


class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'update':
            return QuizDetailSerializer
        return QuizSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_anonymous:
            # Anonymous users can only see public quizzes
            return Quiz.objects.filter(is_public=True)
            
        # Public quizzes OR quizzes created by current user OR quizzes shared with user
        return (Quiz.objects.filter(is_public=True) | 
                Quiz.objects.filter(creator=user) | 
                Quiz.objects.filter(shared_with=user))
    
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
    
    @action(detail=True, methods=['get'])
    def by_share_code(self, request, pk=None):
        """Retrieve a quiz by share code."""
        share_code = pk
        quiz = get_object_or_404(Quiz, share_code=share_code)
        
        # Check if the quiz is public or if the user has access
        if not quiz.is_public:
            if request.user.is_anonymous:
                if not quiz.allow_anonymous_attempts:
                    return Response(
                        {"error": "This quiz is private and requires authentication."}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            elif quiz.creator != request.user and not quiz.shared_with.filter(id=request.user.id).exists():
                return Response(
                    {"error": "You don't have access to this quiz."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
        serializer = self.get_serializer(quiz)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def share(self, request, pk=None):
        """Share a quiz with another user"""
        quiz = self.get_object()
        
        # Validate that the user can share this quiz
        if quiz.creator != request.user and not QuizShare.objects.filter(
            quiz=quiz, 
            shared_with=request.user, 
            permission_type='edit'
        ).exists():
            return Response(
                {"error": "You don't have permission to share this quiz."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get or create user by username or email
        recipient_identifier = request.data.get('shared_with')
        permission_type = request.data.get('permission_type', 'attempt')
        
        try:
            if '@' in recipient_identifier:
                recipient = User.objects.get(email=recipient_identifier)
            else:
                recipient = User.objects.get(username=recipient_identifier)
        except User.DoesNotExist:
            return Response(
                {"error": f"User with identifier '{recipient_identifier}' does not exist."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Create the share
        share_data = {
            'quiz': quiz,
            'shared_with': recipient,
            'permission_type': permission_type,
            'shared_by': request.user
        }
        
        share, created = QuizShare.objects.get_or_create(
            quiz=quiz,
            shared_with=recipient,
            defaults={
                'permission_type': permission_type,
                'shared_by': request.user
            }
        )
        
        if not created:
            # Update permission type if share already exists
            share.permission_type = permission_type
            share.save()
            
        serializer = QuizShareSerializer(share)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def shares(self, request, pk=None):
        """List all shares for a quiz"""
        quiz = self.get_object()
        
        # Check permissions
        if quiz.creator != request.user:
            return Response(
                {"error": "You don't have permission to view shares for this quiz."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        shares = QuizShare.objects.filter(quiz=quiz)
        serializer = QuizShareSerializer(shares, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def shared_with_me(self, request):
        """List all quizzes shared with the current user"""
        quizzes = Quiz.objects.filter(shared_with=request.user)
        serializer = self.get_serializer(quizzes, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """Generate a QR code for sharing the quiz"""
        from .utils import generate_qr_code
        
        quiz = self.get_object()
        share_url = quiz.get_share_link()
        
        # Generate QR code
        qr_code_base64 = generate_qr_code(share_url)
        
        if qr_code_base64:
            return Response({
                'qr_code': qr_code_base64,
                'share_url': share_url,
                'share_code': quiz.share_code
            })
        else:
            return Response(
                {"error": "Failed to generate QR code."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        quiz_id = self.kwargs.get('quiz_pk')
        if quiz_id:
            return Question.objects.filter(quiz_id=quiz_id)
        return Question.objects.none()
    
    def perform_create(self, serializer):
        quiz_id = self.kwargs.get('quiz_pk')
        quiz = get_object_or_404(Quiz, id=quiz_id)
        if quiz.creator != self.request.user:
            raise permissions.PermissionDenied("You can only add questions to your own quizzes.")
        serializer.save(quiz=quiz)


class ChoiceViewSet(viewsets.ModelViewSet):
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        question_id = self.kwargs.get('question_pk')
        if question_id:
            return Choice.objects.filter(question_id=question_id)
        return Choice.objects.none()
    
    def perform_create(self, serializer):
        question_id = self.kwargs.get('question_pk')
        question = get_object_or_404(Question, id=question_id)
        if question.quiz.creator != self.request.user:
            raise permissions.PermissionDenied("You can only add choices to your own quiz questions.")
        serializer.save(question=question)


class ImageUploadView(generics.CreateAPIView):
    serializer_class = ImageUploadSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_upload = serializer.save()
        
        # Process the image with OpenAI
        parsed_data = process_image_with_openai(image_upload.image.path)
        
        # Save the parsed data
        image_upload.parsed_data = parsed_data
        image_upload.processed = True
        image_upload.save()
        
        # Return the parsed data
        return Response({
            "id": image_upload.id,
            "parsed_data": parsed_data
        }, status=status.HTTP_201_CREATED)


class CreateQuizFromImageView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        image_id = request.data.get('image_id')
        title = request.data.get('title', 'Untitled Quiz')
        duration_minutes = int(request.data.get('duration_minutes', 10))
        is_public = request.data.get('is_public', False)
        
        try:
            # Get the image upload
            image_upload = get_object_or_404(ImageUpload, id=image_id, user=request.user)
            
            if not image_upload.processed or not image_upload.parsed_data:
                return Response({"error": "Image has not been processed yet."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create the quiz from parsed data
            with transaction.atomic():
                quiz = create_quiz_from_parsed_data(
                    user=request.user,
                    title=title,
                    parsed_data=image_upload.parsed_data,
                    duration_minutes=duration_minutes,
                    is_public=is_public
                )
                
                if quiz:
                    return Response({
                        "message": "Quiz created successfully",
                        "quiz_id": quiz.id,
                        "share_code": quiz.share_code
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({"error": "Failed to create quiz"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class QuizSessionViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSessionSerializer
    permission_classes = [IsAuthenticated, IsQuizCreatorOrParticipant]
    
    def get_queryset(self):
        user = self.request.user
        # Sessions created by the user or sessions for quizzes created by the user
        return QuizSession.objects.filter(user=user) | QuizSession.objects.filter(quiz__creator=user)
    
    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        session = self.get_object()
        
        # Check if the quiz session is already completed or timed out
        if session.is_completed:
            return Response({"error": "This quiz session is already completed."}, status=status.HTTP_400_BAD_REQUEST)
        
        if session.is_timed_out:
            complete_quiz_session(session)
            return Response({"error": "Time's up! The quiz session has expired."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get question and choice from request data
        question_id = request.data.get('question_id')
        choice_id = request.data.get('choice_id')
        
        if not question_id or not choice_id:
            return Response({"error": "Question ID and Choice ID are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate that the question belongs to the quiz
        try:
            question = Question.objects.get(id=question_id, quiz=session.quiz)
        except Question.DoesNotExist:
            return Response({"error": "Invalid question for this quiz"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate that the choice belongs to the question
        try:
            choice = Choice.objects.get(id=choice_id, question=question)
        except Choice.DoesNotExist:
            return Response({"error": "Invalid choice for this question"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Record the answer (update if already exists)
        user_answer, created = UserAnswer.objects.update_or_create(
            session=session,
            question=question,
            defaults={'selected_choice': choice}
        )
        
        # Return the answer details
        serializer = UserAnswerSerializer(user_answer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        session = self.get_object()
        
        # Check if the session is already completed
        if session.is_completed:
            return Response({"error": "This session is already completed"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Complete the session and calculate score
        session = complete_quiz_session(session)
        
        # Return the session details with score
        serializer = QuizSessionResultSerializer(session)
        return Response(serializer.data)
