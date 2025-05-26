from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Quiz, Question, Choice, ImageUpload, QuizSession, UserAnswer, QuizShare


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def validate(self, data):
        if data['password'] != data.pop('password2'):
            raise serializers.ValidationError({'password': 'Passwords must match.'})
        return data
        
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'choices']


class QuizSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    questions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = ['id', 'title', 'creator', 'created_at', 'updated_at', 
                  'duration_minutes', 'is_public', 'share_code', 'questions_count']
    
    def get_questions_count(self, obj):
        return obj.questions.count()


class QuizDetailSerializer(QuizSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta(QuizSerializer.Meta):
        fields = QuizSerializer.Meta.fields + ['questions']


class ImageUploadSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        allow_empty_file=False,
        use_url=True,
    )
    
    class Meta:
        model = ImageUpload
        fields = ['id', 'image', 'uploaded_at', 'processed', 'parsed_data']
        read_only_fields = ['id', 'uploaded_at', 'processed', 'parsed_data']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserAnswerSerializer(serializers.ModelSerializer):
    is_correct = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'selected_choice', 'answered_at', 'is_correct']
        read_only_fields = ['id', 'answered_at', 'is_correct']


class QuizSessionSerializer(serializers.ModelSerializer):
    answers = UserAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuizSession
        fields = ['id', 'quiz', 'user', 'started_at', 'completed_at', 'score', 'answers']
        read_only_fields = ['id', 'user', 'started_at', 'completed_at', 'score']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class QuizSessionResultSerializer(serializers.ModelSerializer):
    quiz = QuizSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    answers = UserAnswerSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()
    correct_answers = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizSession
        fields = ['id', 'quiz', 'user', 'started_at', 'completed_at', 
                  'score', 'answers', 'total_questions', 'correct_answers']
    
    def get_total_questions(self, obj):
        return obj.quiz.questions.count()
    
    def get_correct_answers(self, obj):
        return obj.answers.filter(selected_choice__is_correct=True).count()


class QuizShareSerializer(serializers.ModelSerializer):
    shared_with_user = UserSerializer(source='shared_with', read_only=True)
    shared_by_user = UserSerializer(source='shared_by', read_only=True)
    
    class Meta:
        model = QuizShare
        fields = ['id', 'quiz', 'shared_with', 'shared_with_user',
                  'shared_by', 'shared_by_user', 'shared_at', 'permission_type']
        read_only_fields = ['id', 'shared_at', 'shared_by', 'shared_by_user']
        
    def validate(self, data):
        # Ensure user isn't sharing with themselves
        if data['shared_with'] == self.context['request'].user:
            raise serializers.ValidationError("You cannot share a quiz with yourself.")
        
        # Ensure user has permission to share
        quiz = data['quiz']
        user = self.context['request'].user
        
        if quiz.creator != user:
            # Check if the user has edit permissions through a share
            share_exists = QuizShare.objects.filter(
                quiz=quiz,
                shared_with=user,
                permission_type='edit'
            ).exists()
            
            if not share_exists:
                raise serializers.ValidationError("You don't have permission to share this quiz.")
                
        return data
        
    def create(self, validated_data):
        validated_data['shared_by'] = self.context['request'].user
        return super().create(validated_data)
