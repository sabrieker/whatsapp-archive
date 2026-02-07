# WhatsApp Archive Web Application - Project Context

## Overview
A WhatsApp Web-like archive viewer for reading/searching exported WhatsApp chats. Supports sharing with group members via shareable links.

## Tech Stack
- **Backend**: FastAPI (Python 3.13+) with async SQLAlchemy
- **Database**: PostgreSQL (configure via `WH_ARCH_ENV_FILE` or `.env`)
- **Storage**: MinIO (configure via `WH_ARCH_ENV_FILE` or `.env`)
- **Frontend**: React 18 + Vite + TailwindCSS + React Query

## Project Structure
```
whatsapp-archive/
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # FastAPI app entry
│       ├── config.py            # Environment settings
│       ├── database.py          # Async SQLAlchemy setup
│       ├── models/              # SQLAlchemy models
│       │   ├── conversation.py
│       │   ├── participant.py
│       │   ├── message.py
│       │   ├── media.py
│       │   └── import_job.py
│       ├── schemas/             # Pydantic schemas
│       ├── api/                 # FastAPI routers
│       │   ├── __init__.py      # Router aggregation
│       │   ├── conversations.py
│       │   ├── messages.py
│       │   ├── import_.py
│       │   ├── search.py
│       │   ├── media.py
│       │   ├── shared.py
│       │   └── analytics.py
│       └── services/            # Business logic
│           ├── parser.py        # WhatsApp export parser
│           ├── storage.py       # MinIO storage service
│           ├── search.py        # Search service (ILIKE)
│           ├── importer.py      # Import orchestrator
│           └── analytics.py     # Chart generation
└── frontend/
    ├── package.json
    └── src/
        ├── api/client.ts        # API client with types
        ├── pages/
        │   ├── HomePage.tsx
        │   ├── ChatPage.tsx
        │   └── SharedChatPage.tsx
        └── components/
            ├── chat/
            │   ├── ChatList.tsx
            │   ├── MessageList.tsx   # Virtual scroll
            │   └── MessageBubble.tsx # WhatsApp-style bubbles
            ├── import/
            │   ├── ImportDialog.tsx
            │   └── ImportProgress.tsx
            ├── analytics/
            │   └── AnalyticsDialog.tsx
            └── ui/
                └── SearchBar.tsx
```

## Database Schema
```sql
-- conversations: Chat metadata
id, name, is_group, share_token, message_count, first_message_at, last_message_at, created_at

-- participants: Chat members with assigned colors
id, conversation_id, name, phone_number, message_count, color, created_at

-- messages: Individual messages with FTS support
id, conversation_id, participant_id, sender_name, content, message_type, timestamp, has_media, search_vector

-- media_files: Media attachments stored in MinIO
id, message_id, storage_key, media_type, mime_type, file_size, original_filename

-- import_jobs: Track import progress
id, conversation_id, status, filename, file_size, total_chunks, uploaded_chunks, total_messages, processed_messages, total_media, processed_media, error_message, created_at, completed_at
```

## Key API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/conversations` | List conversations (paginated) |
| GET | `/api/conversations/{id}` | Get conversation details |
| PATCH | `/api/conversations/{id}` | Rename conversation |
| DELETE | `/api/conversations/{id}` | Delete conversation |
| POST | `/api/conversations/{id}/share` | Generate share token |
| GET | `/api/messages/conversation/{id}` | Get messages (paginated) |
| GET | `/api/search?q=&conversation_id=` | Search messages (ILIKE) |
| POST | `/api/import/upload/simple` | Upload small files directly |
| POST | `/api/import/init` | Initialize chunked upload |
| POST | `/api/import/upload/chunk` | Upload chunk |
| POST | `/api/import/start` | Start background import |
| GET | `/api/import/progress/{id}` | Get import progress |
| GET | `/api/media/{id}` | Get media file (presigned URL) |
| GET | `/api/shared/{token}` | Public shared view |
| GET | `/api/analytics/{id}/participants` | Get participants for analytics |
| POST | `/api/analytics/{id}?person1=&person2=` | Generate analytics charts |

## Critical Implementation Details

### WhatsApp Parser (parser.py)
Handles multiple date formats and Unicode issues:

```python
# Supported formats
DATETIME_FORMATS = [
    "%d.%m.%Y, %H:%M:%S",  # Turkish: 24.01.2024, 15:30:45
    "%d.%m.%Y, %H:%M",     # Turkish short
    "%d/%m/%Y, %H:%M:%S",  # UK format
    "%d/%m/%Y, %H:%M",     # UK short
    "%m/%d/%Y, %H:%M:%S",  # US format
    "%m/%d/%Y, %H:%M",     # US short
]

# CRITICAL: WhatsApp exports contain invisible Unicode characters
UNICODE_STRIP_CHARS = '\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff'

def clean_unicode(text: str) -> str:
    """Remove invisible Unicode formatting characters."""
    for char in UNICODE_STRIP_CHARS:
        text = text.replace(char, '')
    return text
```

### Media Linking (importer.py)
Fixed by using `db.flush()` to get message IDs before mapping:

```python
async def _import_messages(self, db, job, conversation, messages) -> dict[str, int]:
    """Import messages in batches. Returns map of media filename to message ID."""
    # ... batch processing ...
    db.add_all(batch)
    await db.flush()  # CRITICAL: Flush to get IDs before mapping
    for i, msg in enumerate(batch):
        # Now msg.id is populated
```

### Search (search.py)
Uses ILIKE instead of FTS for Turkish language support:

```python
query = (
    select(Message)
    .options(selectinload(Message.media_files))  # Eager load to avoid MissingGreenlet
    .where(Message.content.ilike(f"%{search_query}%"))
)
```

### Analytics (analytics.py)
Server-side chart generation with Matplotlib/Seaborn. Adaptive for long time spans:
- Calendar heatmaps split by year for 7+ year chats
- Quarterly resampling for trend charts
- Uses PNG images stored in MinIO with presigned URLs

**Two modes:**
1. **Group Stats** (no person selection): Shows overall participation, top participants chart, participation over time
2. **Compare 2 People**: Shows comparison heatmap, response time analysis

**Charts generated:**
- `time_heatmap`: Hour x Day of week activity
- `calendar_heatmaps`: Per-year activity calendars
- `trend`: Monthly/Quarterly message volume (by top 5 senders)
- `daily_activity`: Rolling average activity
- `top_participants`: Bar chart + pie chart of top contributors
- `participation_over_time`: Stacked area chart
- `comparison_heatmap`: Who messages more at each time (comparison mode only)
- `response_time`: Average response time by hour (comparison mode only)

**Important:** All numpy types must be converted to Python native types for JSON serialization using `_to_native_types()` helper.

## Known Issues & Fixes Applied

1. **Python 3.13 compatibility**: Updated asyncpg>=0.30.0, pydantic>=2.10.0
2. **MissingGreenlet errors**: Always use `selectinload()` for relationships
3. **Unicode parsing failures**: Apply `clean_unicode()` before parsing
4. **Single-digit dates**: Regex fallback parser for dates like `[5.10.2024, ...]`
5. **Media not linking**: Use `db.flush()` before accessing auto-generated IDs

## Running the Project

All operations use the single `start.py` script:

```bash
cd whatsapp-archive

# Configure (choose one):
cp .env.example .env                    # Option A: local .env file
export WH_ARCH_ENV_FILE=/path/to/.env   # Option B: external config

# First time setup
python start.py init

# Start development servers
python start.py dev

# Other commands
python start.py backend   # Backend only (port 8000)
python start.py frontend  # Frontend only (port 5173)
python start.py check     # Verify config and dependencies
python start.py help      # Show help
```

**Required services:**
- PostgreSQL (configure in .env)
- MinIO (configure in .env)

## Pending Features (Backlog)

### FEATURE-001: Conversation Merge/Append
Documented in `/docs/features/FEATURE-001-conversation-merge.md`
- Append new exports to existing conversations
- Handle duplicate detection
- Support incremental imports

## UI Features
- WhatsApp Web-style message bubbles with avatars (initials)
- Message grouping by sender
- Thumbnail media with lightbox
- Rename conversations (click header)
- Analytics dialog with charts
- Share link generation
- Search within conversation
