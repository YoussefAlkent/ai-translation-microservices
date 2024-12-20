# AI Translation Micro-Services Project

## Description
A application project that provides text summarization and translation services. The project includes multiple microservices for handling different functionalities such as text summarization, English to Arabic translation, and Arabic to English translation.

## Features
- **Text Summarization**: Summarize large texts into concise summaries with different styles (formal, informal, technical, executive, creative).
- **English to Arabic Translation**: Translate English text to Arabic with different levels of formality (formal, neutral, informal).
- **Arabic to English Translation**: Translate Arabic text to English with different levels of formality (formal, neutral, informal).

## Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/cloud-project.git

# Navigate to the project directory
cd cloud-project

# Install dependencies
npm install

# Start the services using Docker Compose
docker-compose up --build
```

## Usage
```bash
# Access the application at http://localhost:4200 for the frontend
# Access the API Gateway at http://localhost:8080
```

## Microservices
- **Text Summarizer**: Handles text summarization requests.
- **English to Arabic Translator**: Handles translation from English to Arabic.
- **Arabic to English Translator**: Handles translation from Arabic to English.
- **API Gateway**: Routes requests to the appropriate microservice.
- **User Service**: Manages user authentication and authorization.

## Environment Variables
The following environment variables are used in the project:

- `OLLAMA_API_URL`: URL for the Ollama API.
- `MODEL_NAME`: Name of the model used for text generation.
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers.
- `JAEGER_HOST`: Host for Jaeger tracing.
- `DATABASE_URL`: Database connection URL for the user service.
- `SUPERTOKENS_API_KEY`: API key for SuperTokens.
- `SUPERTOKENS_API_KEY_DYNAMIC`: Dynamic API key for SuperTokens.

## API Endpoints
### Text Summarizer
- `POST /api/v1/summarize`: Summarize text.
- `GET /api/v1/summarize/status/{request_id}`: Get the status of a summarization request.

### English to Arabic Translator
- `POST /api/v1/translate/english-to-arabic`: Translate English text to Arabic.
- `GET /api/v1/translate/english-to-arabic/status/{request_id}`: Get the status of an English to Arabic translation request.

### Arabic to English Translator
- `POST /api/v1/translate/arabic-to-english`: Translate Arabic text to English.
- `GET /api/v1/translate/arabic-to-english/status/{request_id}`: Get the status of an Arabic to English translation request.

### User Service
- `POST /auth/signup`: Sign up a new user.
- `POST /auth/signin`: Sign in an existing user.

## Contributing
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.
