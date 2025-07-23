# CSI LangGraph Application

A production-ready AI-powered Customer Service Intelligence (CSI) application built with LangGraph, FastAPI, and MongoDB.

## Features

- **AI-Powered Chat Interface**: Natural language processing for CSI operations
- **CRUD Operations**: Complete Create, Read, Update, Delete operations for CSI cases
- **Approval Workflow**: Case approval and BDM sign-off processes
- **MongoDB Integration**: Robust database operations with error handling
- **Session Management**: Persistent chat sessions with memory
- **Production Ready**: Comprehensive error handling, logging, and monitoring

## Architecture

- **LangGraph**: Workflow orchestration and AI agent management
- **FastAPI**: High-performance web framework
- **MongoDB**: Document database for CSI cases and approved cases
- **OpenAI**: Language model for natural language processing
- **Pydantic**: Data validation and serialization

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd lang-graph-demo
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env file with your actual values
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# MongoDB Configuration
MONGODB_URI=mongodb://username:password@host:port/
MONGODB_DB=your_database_name

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Logging Configuration
LOG_LEVEL=INFO
```

## Usage

### Development Mode

```bash
# Using the startup script
python start_server.py

# Or using uvicorn directly
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Set DEBUG=False in .env file
python start_server.py
```

## API Endpoints

### Chat Endpoint
- **POST** `/chat`
  - Send messages to the AI agent
  - Handles CSI operations through natural language

### Session Management
- **DELETE** `/session/{session_id}`
  - Clear session history and agent instance

### Health Check
- **GET** `/health`
  - Check application health status

### Statistics
- **GET** `/session/{session_id}/stats`
  - Get session statistics

### Form Fields
- **GET** `/form-fields`
  - Get available form fields for CSI cases

### Case Operations
- **POST** `/upsert-case`
  - Create or update CSI cases

## Supported Operations

The AI agent can handle the following operations through natural language:

1. **Create CSI Cases**: "Create a new case for customer ABC"
2. **Read CSI Cases**: "Show me cases for customer XYZ"
3. **Update CSI Cases**: "Update case ID 12345 with new information"
4. **Approve Cases**: "Approve case ID 12345"
5. **Delete Cases**: "Delete case ID 12345"
6. **BDM Sign-off**: "Submit case for BDM approval"
7. **General Chat**: Casual conversation and help

## Database Collections

- **cases**: Main collection for CSI cases
- **approved_cases**: Collection for approved CSI cases

## Error Handling

The application includes comprehensive error handling:

- Database connection errors
- MongoDB operation errors
- LangGraph workflow errors
- API validation errors
- Tool execution errors

## Logging

Structured logging is implemented throughout the application:

- Console output for development
- File logging for production
- Error tracking with stack traces
- Performance monitoring

## Development

### Project Structure

```
lang-graph-demo/
├── main.py              # LangGraph agent implementation
├── server.py            # FastAPI server
├── start_server.py      # Production startup script
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
├── README.md           # This file
├── crud/               # CRUD operations
│   ├── cases_crud.py
│   └── approved_csi_crud.py
├── tools/              # LangGraph tools
│   ├── csi_tools.py
│   ├── dynamic_updates_tool.py
│   └── send_email_tool.py
├── db/                 # Database connection
│   └── connection.py
└── logs/               # Log files (created at runtime)
```

### Adding New Tools

1. Create tool function in `tools/` directory
2. Import and register in `main.py`
3. Add tool logic to `_execute_tools` method
4. Update intent classification if needed

### Testing

```bash
# Test database connection
python -c "from db.connection import get_db_connection; print('DB OK')"

# Test API endpoints
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "message": "Hello"}'
```

## Production Deployment

1. Set up MongoDB instance
2. Configure environment variables
3. Set `DEBUG=False`
4. Use process manager (PM2, systemd, etc.)
5. Set up reverse proxy (nginx)
6. Configure SSL certificates
7. Set up monitoring and alerts

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check MONGODB_URI in .env
   - Verify database credentials
   - Ensure MongoDB is running

2. **OpenAI API Errors**
   - Verify OPENAI_API_KEY
   - Check API quota and billing

3. **Import Errors**
   - Ensure virtual environment is activated
   - Install all requirements: `pip install -r requirements.txt`

4. **Tool Execution Errors**
   - Check logs for detailed error messages
   - Verify database collections exist
   - Validate input data format

### Logs

Check application logs:
- Console output during development
- `app.log` file for production logs
- MongoDB logs for database issues

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with proper error handling
4. Add tests if applicable
5. Update documentation
6. Submit pull request

## License

[Add your license information here]

## Support

For support and questions:
- Check the logs for error details
- Review the troubleshooting section
- Create an issue in the repository
