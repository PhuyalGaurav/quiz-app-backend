from django.contrib import admin
from .models import Quiz, Question, Choice, ImageUpload, QuizSession, UserAnswer, QuizShare

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('text', 'quiz', 'order')
    list_filter = ('quiz',)
    search_fields = ('text',)

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True

class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'created_at', 'duration_minutes', 'is_public', 'share_code')
    list_filter = ('is_public', 'creator')
    search_fields = ('title',)
    inlines = [QuestionInline]
    readonly_fields = ('share_code',)

class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    extra = 0
    readonly_fields = ('question', 'selected_choice', 'is_correct', 'answered_at')

class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'started_at', 'completed_at', 'score')
    list_filter = ('quiz', 'user', 'completed_at')
    search_fields = ('quiz__title', 'user__username')
    readonly_fields = ('score',)
    inlines = [UserAnswerInline]

class ImageUploadAdmin(admin.ModelAdmin):
    list_display = ('user', 'uploaded_at', 'processed')
    list_filter = ('processed', 'user')
    readonly_fields = ('parsed_data',)

class QuizShareAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'shared_by', 'shared_with', 'shared_at', 'permission_type')
    list_filter = ('permission_type', 'shared_at')
    search_fields = ('quiz__title', 'shared_by__username', 'shared_with__username')

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
admin.site.register(ImageUpload, ImageUploadAdmin)
admin.site.register(QuizSession, QuizSessionAdmin)
admin.site.register(UserAnswer)
admin.site.register(QuizShare, QuizShareAdmin)
