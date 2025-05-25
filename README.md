# Quiz App Backend

A robust quiz application API built with Django REST Framework that provides JWT authentication, OpenAI integration for parsing MCQs from images, timed quizzes, and sharing capabilities.

## Features

- User authentication with JWT tokens
- Upload and process images of MCQs using OpenAI's Vision API
- Create, edit, and manage quizzes
- Share quizzes with other users via unique codes
- Generate QR codes for easy sharing
- Take quizzes within a time limit
- Score tracking and result analysis
- AWS S3 integration for media storage

## Installation

1. Clone the repository:
```
git clone https://github.com/phuyalgaurav/quiz-app-backend.git
cd quiz-app-backend
```

2. Set up a virtual environment:
```
python -m venv env
source env/bin/activate  # On Windows, use `env\Scripts\activate`
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```
# Django settings
SECRET_KEY=your_secret_key
DEBUG=True

# OpenAI settings
OPENAI_API_KEY=your_openai_api_key

# AWS settings
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=your_aws_region

# Frontend URL for share links
FRONTEND_URL=https://your-frontend-url.com
```

5. Run migrations:
```
python manage.py migrate
```

6. Create a superuser:
```
python manage.py createsuperuser
```

7. Run the server:
```
python manage.py runserver
```

## API Documentation

The API is documented using Swagger UI, which can be accessed at:

- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

These interactive documentation pages will show all available endpoints, request/response schemas, and allow you to test the API directly.

### Authentication

- `POST /api/token/`: Get JWT tokens with username and password
- `POST /api/token/refresh/`: Refresh an expired JWT token
- `POST /api/register/`: Register a new user
- `GET/PUT /api/profile/`: View or update the current user's profile

### Quiz Management

- `GET /api/quizzes/`: List all accessible quizzes
- `POST /api/quizzes/`: Create a new quiz
- `GET /api/quizzes/{id}/`: Get details of a specific quiz
- `PUT /api/quizzes/{id}/`: Update a quiz
- `DELETE /api/quizzes/{id}/`: Delete a quiz
- `GET /api/quizzes/shared_with_me/`: List quizzes shared with the current user

### Image Processing

- `POST /api/upload-image/`: Upload an image for MCQ extraction
- `POST /api/create-quiz-from-image/`: Create a quiz from a processed image

### Quiz Sharing

- `POST /api/quizzes/{id}/share/`: Share a quiz with another user
- `GET /api/quizzes/{id}/shares/`: View all shares for a quiz
- `GET /api/quizzes/{id}/qr_code/`: Generate a QR code for sharing
- `GET /api/join/{share_code}/`: Join a quiz using a share code

### Quiz Taking

- `POST /api/sessions/`: Create a new quiz session
- `GET /api/sessions/{id}/`: Get details of a quiz session
- `POST /api/sessions/{id}/submit-answer/`: Submit an answer for a question
- `POST /api/sessions/{id}/complete/`: Complete a quiz session

## Mobile App Integration

This backend is designed to integrate with a mobile app frontend. The API endpoints follow REST conventions and use JWT for authentication, making it compatible with most mobile development frameworks.

### React Native Integration

For detailed instructions on integrating with a React Native mobile app, see:

- [Mobile Integration Guide](MOBILE_INTEGRATION.md)
- [React Native Integration](docs/REACT_NATIVE_INTEGRATION.md)
- [Mobile App Best Practices](docs/MOBILE_APP_BEST_PRACTICES.md)

Key features for mobile integration:
- JWT authentication for secure mobile login
- Image upload and processing with OpenAI Vision API
- QR code generation for easy quiz sharing
- Deep linking support for opening shared quizzes
- Push notification hooks (requires additional setup)

## Security Considerations

- API keys and credentials should be kept secure
- Always rotate compromised keys immediately
- Enable CORS for specific origins in production
- Use HTTPS in production

## License

MIT
