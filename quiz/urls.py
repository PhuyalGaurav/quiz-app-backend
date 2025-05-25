from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'quizzes', views.QuizViewSet)
router.register(r'shares', views.QuizShareViewSet, basename='quizshare')

urlpatterns = [
    # JWT Authentication
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User registration and profile
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    
    # Image upload and processing
    path('upload-image/', views.ImageUploadView.as_view(), name='upload-image'),
    path('create-quiz-from-image/', views.CreateQuizFromImageView.as_view(), name='create-quiz-from-image'),
    
    # Quiz sharing
    path('join/<str:share_code>/', views.JoinQuizByShareCodeView.as_view(), name='join-quiz'),
    
    # Quiz routes
    path('', include(router.urls)),
    
    # Quiz sessions
    path('sessions/', views.QuizSessionViewSet.as_view({'get': 'list', 'post': 'create'}), name='quiz-sessions'),
    path('sessions/<uuid:pk>/', views.QuizSessionViewSet.as_view({
        'get': 'retrieve', 
        'put': 'update', 
        'delete': 'destroy'
    }), name='quiz-session-detail'),
    path('sessions/<uuid:pk>/submit-answer/', views.QuizSessionViewSet.as_view({'post': 'submit_answer'}), name='submit-answer'),
    path('sessions/<uuid:pk>/complete/', views.QuizSessionViewSet.as_view({'post': 'complete'}), name='complete-session'),
    
    # Nested routes for questions and choices
    path('quizzes/<uuid:quiz_pk>/questions/', views.QuestionViewSet.as_view({
        'get': 'list', 
        'post': 'create'
    }), name='quiz-questions'),
    path('quizzes/<uuid:quiz_pk>/questions/<uuid:pk>/', views.QuestionViewSet.as_view({
        'get': 'retrieve', 
        'put': 'update', 
        'delete': 'destroy'
    }), name='question-detail'),
    
    path('questions/<uuid:question_pk>/choices/', views.ChoiceViewSet.as_view({
        'get': 'list', 
        'post': 'create'
    }), name='question-choices'),
    path('questions/<uuid:question_pk>/choices/<uuid:pk>/', views.ChoiceViewSet.as_view({
        'get': 'retrieve', 
        'put': 'update', 
        'delete': 'destroy'
    }), name='choice-detail'),
]
