# WhatsApp Archive Viewer

A beautiful, WhatsApp Web-style archive viewer for reading and searching your exported WhatsApp chats. Self-hosted, private, and shareable with group members.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.115+-green.svg)

## Features

- **WhatsApp Web UI** - Familiar interface with message bubbles, avatars, and grouping
- **Full-text Search** - Search through hundreds of thousands of messages instantly
- **Media Support** - View images, videos, and other attachments from your exports
- **Analytics Dashboard** - Visualize chat patterns with heatmaps and charts
- **Shareable Links** - Generate read-only links to share conversations with others
- **Large File Support** - Handle exports of any size with chunked uploads
- **Multi-format Parsing** - Supports various WhatsApp export date formats

## Screenshots

<!-- TODO: Add screenshots -->
*Coming soon*

## Quick Start

### Prerequisites

- Docker and Docker Compose
- PostgreSQL (or use Docker)
- MinIO (or use Docker)

### Using Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/sabrieker/whatsapp-archive.git
   cd whatsapp-archive
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your configuration:
   ```bash
   # Generate a secure secret key
   SECRET_KEY=$(openssl rand -hex 32)
   ```

4. Start the services:
   ```bash
   docker-compose up -d
   ```

5. Open http://localhost:5173 in your browser

### Local Development

All operations use the single `start.py` script:

```bash
# 1. Set up config (choose one):

# Option A: Create .env in project root
cp .env.example .env
# Edit .env with your settings

# Option B: Use external config file
export WH_ARCH_ENV_FILE=/path/to/your/config.env

# 2. Initialize (first time only)
python start.py init

# 3. Start development servers
python start.py dev
```

#### Available Commands

| Command | Description |
|---------|-------------|
| `python start.py init` | First-time setup: install dependencies, create database |
| `python start.py dev` | Start both backend and frontend |
| `python start.py backend` | Start backend only (port 8000) |
| `python start.py frontend` | Start frontend only (port 5173) |
| `python start.py check` | Verify configuration and dependencies |
| `python start.py help` | Show detailed help |

#### Manual Setup (Alternative)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables (or create .env file in project root)
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/whatsapp_archive
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=your-access-key
export MINIO_SECRET_KEY=your-secret-key

# Start the server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `MINIO_ENDPOINT` | MinIO server address | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | Required |
| `MINIO_SECRET_KEY` | MinIO secret key | Required |
| `MINIO_BUCKET` | Storage bucket name | `whatsapp-archive` |
| `MINIO_SECURE` | Use HTTPS for MinIO | `false` |
| `SECRET_KEY` | Application secret key | Required |
| `DEBUG` | Enable debug mode | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

## Usage

### Importing Chats

1. Export your WhatsApp chat:
   - Open WhatsApp > Chat > More > Export chat
   - Choose "Include media" for full archive
   - Save the ZIP file

2. Upload in the app:
   - Click "Import" on the home page
   - Select your ZIP file or text file
   - Wait for processing to complete

### Viewing Analytics

1. Open a conversation
2. Click the chart icon in the header
3. View activity heatmaps, trends, and participant stats

### Sharing

1. Open a conversation
2. Click the share icon
3. Copy the generated link
4. Anyone with the link can view (read-only)

## Tech Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL with async SQLAlchemy
- MinIO for object storage
- Matplotlib/Seaborn for analytics charts

**Frontend:**
- React 18 with TypeScript
- Vite for building
- TailwindCSS for styling
- React Query for state management

## Project Structure

```
whatsapp-archive/
├── backend/
│   └── app/
│       ├── api/          # FastAPI routes
│       ├── models/       # SQLAlchemy models
│       ├── schemas/      # Pydantic schemas
│       └── services/     # Business logic
├── frontend/
│   └── src/
│       ├── api/          # API client
│       ├── components/   # React components
│       └── pages/        # Page components
├── docs/                 # Documentation
└── docker-compose.yml
```

## API Documentation

When running the backend, API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

- [ ] Conversation merge/append feature
- [ ] Export analytics as PDF
- [ ] Dark mode
- [ ] Mobile app
- [ ] End-to-end encryption for shared links

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- WhatsApp for the chat export feature
- The FastAPI and React communities
