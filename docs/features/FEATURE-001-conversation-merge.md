# FEATURE-001: Conversation Merge / Append Import

## Status: Backlog
## Priority: High
## Estimated Effort: 2-3 days

---

## 1. Problem Statement

Users export WhatsApp chats periodically (e.g., yearly backups). When they import a new export of the same conversation, the current system creates a **duplicate conversation** instead of merging new messages into the existing archive.

### Current Behavior
```
Import 1 (Jan 2024): "Family Group" → Creates Conversation ID 1 (50,000 messages)
Import 2 (Jan 2025): "Family Group" → Creates Conversation ID 2 (60,000 messages, includes 50K duplicates)
```

### Desired Behavior
```
Import 1 (Jan 2024): "Family Group" → Creates Conversation ID 1 (50,000 messages)
Import 2 (Jan 2025): "Family Group" → Merges into Conversation ID 1 (60,000 messages, only 10K new)
```

---

## 2. User Stories

### US-1: Merge Import into Existing Conversation
**As a** user with an existing archived conversation
**I want to** import a newer export and merge it with my existing archive
**So that** I have a single, complete conversation history without duplicates

### US-2: Choose Merge Target
**As a** user importing a chat
**I want to** choose which existing conversation to merge into (if multiple similar ones exist)
**So that** I have control over the merge process

### US-3: Preview Merge Results
**As a** user
**I want to** see how many new messages will be added before confirming the merge
**So that** I can verify the merge makes sense

### US-4: Merge Conflict Resolution
**As a** user
**I want** the system to handle edge cases (time zone differences, edited messages)
**So that** I don't lose any messages or create duplicates

---

## 3. Technical Design

### 3.1 Duplicate Detection Strategy

WhatsApp messages don't have unique IDs in exports. We must detect duplicates using a **composite key**:

```python
# Duplicate detection hash
def message_hash(message: ParsedMessage) -> str:
    """
    Generate a hash for duplicate detection.

    Components:
    - timestamp (rounded to minute to handle minor time variations)
    - sender_name (normalized: lowercase, stripped)
    - content (first 100 chars, normalized)
    """
    ts_rounded = message.timestamp.replace(second=0, microsecond=0)
    sender_normalized = message.sender_name.lower().strip()
    content_normalized = (message.content or "")[:100].lower().strip()

    hash_input = f"{ts_rounded.isoformat()}|{sender_normalized}|{content_normalized}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:32]
```

### 3.2 Database Schema Changes

#### New Column: `messages.content_hash`
```sql
ALTER TABLE messages ADD COLUMN content_hash VARCHAR(32);
CREATE INDEX ix_messages_content_hash ON messages(conversation_id, content_hash);
```

#### New Table: `merge_jobs`
```sql
CREATE TABLE merge_jobs (
    id SERIAL PRIMARY KEY,
    source_import_job_id INTEGER REFERENCES import_jobs(id),
    target_conversation_id INTEGER REFERENCES conversations(id),
    status VARCHAR(50) DEFAULT 'pending',  -- pending, analyzing, merging, completed, failed

    -- Analysis results
    total_messages_in_import INTEGER DEFAULT 0,
    duplicate_messages INTEGER DEFAULT 0,
    new_messages INTEGER DEFAULT 0,
    new_media_files INTEGER DEFAULT 0,

    -- Progress tracking
    processed_messages INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Error handling
    error_message TEXT
);
```

### 3.3 Merge Algorithm

```
┌─────────────────────────────────────────────────────────────────┐
│                      MERGE IMPORT FLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. UPLOAD PHASE (existing)
   └── User uploads .txt or .zip file
   └── File stored in MinIO

2. ANALYSIS PHASE (new)
   ├── Parse file to extract conversation name
   ├── Search for existing conversations with similar names
   │   └── Fuzzy match: Levenshtein distance < 3 OR contains match
   ├── If matches found:
   │   └── Return list of potential merge targets to frontend
   └── If no matches:
       └── Proceed with normal import (create new conversation)

3. MERGE DECISION (new - frontend)
   └── User sees dialog:
       ┌─────────────────────────────────────────────┐
       │  Similar conversation found!                │
       │                                             │
       │  "Family Group" (45,231 messages)           │
       │  Last message: Dec 15, 2024                 │
       │                                             │
       │  [Merge into existing]  [Create new]        │
       └─────────────────────────────────────────────┘

4. MERGE ANALYSIS PHASE (new)
   ├── Parse all messages from import file
   ├── Generate content_hash for each message
   ├── Query existing hashes:
   │   SELECT content_hash FROM messages WHERE conversation_id = ?
   ├── Calculate:
   │   ├── new_messages = import_hashes - existing_hashes
   │   └── duplicate_messages = import_hashes ∩ existing_hashes
   └── Return analysis to frontend for confirmation

5. USER CONFIRMATION (new - frontend)
   └── User sees:
       ┌─────────────────────────────────────────────┐
       │  Merge Analysis Complete                    │
       │                                             │
       │  Messages in import: 52,000                 │
       │  Already in archive: 45,000                 │
       │  New messages to add: 7,000                 │
       │  New media files: 234                       │
       │                                             │
       │  [Confirm Merge]  [Cancel]                  │
       └─────────────────────────────────────────────┘

6. MERGE EXECUTION PHASE (new)
   ├── Insert only new messages (WHERE hash NOT IN existing)
   ├── Update participants' message_count
   ├── Update conversation metadata:
   │   ├── message_count += new_messages
   │   ├── last_message_at = MAX(existing, new)
   │   └── first_message_at = MIN(existing, new)
   ├── Import new media files
   └── Update search vectors for new messages

7. COMPLETION
   └── Return merge summary to user
```

### 3.4 API Changes

#### New Endpoints

```
POST /api/import/analyze
```
**Request:**
```json
{
  "job_id": 123
}
```
**Response:**
```json
{
  "job_id": 123,
  "detected_conversation_name": "Family Group",
  "potential_merge_targets": [
    {
      "id": 1,
      "name": "Family Group",
      "message_count": 45231,
      "last_message_at": "2024-12-15T18:30:00Z",
      "similarity_score": 1.0
    },
    {
      "id": 5,
      "name": "Family Group 2023",
      "message_count": 12000,
      "last_message_at": "2023-12-31T23:59:00Z",
      "similarity_score": 0.85
    }
  ]
}
```

---

```
POST /api/import/merge/analyze
```
**Request:**
```json
{
  "job_id": 123,
  "target_conversation_id": 1
}
```
**Response:**
```json
{
  "merge_job_id": 456,
  "status": "analyzed",
  "total_messages_in_import": 52000,
  "duplicate_messages": 45000,
  "new_messages": 7000,
  "new_media_files": 234,
  "new_participants": ["Uncle Bob"],
  "date_range": {
    "import_first": "2023-01-01T00:00:00Z",
    "import_last": "2025-01-01T00:00:00Z",
    "existing_first": "2023-01-01T00:00:00Z",
    "existing_last": "2024-12-15T18:30:00Z",
    "overlap_start": "2023-01-01T00:00:00Z",
    "overlap_end": "2024-12-15T18:30:00Z"
  }
}
```

---

```
POST /api/import/merge/execute
```
**Request:**
```json
{
  "merge_job_id": 456
}
```
**Response:**
```json
{
  "merge_job_id": 456,
  "status": "processing"
}
```

---

```
GET /api/import/merge/progress/{merge_job_id}
```
**Response:**
```json
{
  "merge_job_id": 456,
  "status": "merging",
  "progress_percent": 65.5,
  "new_messages": 7000,
  "processed_messages": 4585,
  "new_media_files": 234,
  "processed_media": 120
}
```

### 3.5 Backend Implementation Files

#### New Files to Create:

1. **`backend/app/models/merge_job.py`**
```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base


class MergeJob(Base):
    __tablename__ = "merge_jobs"

    id = Column(Integer, primary_key=True, index=True)
    source_import_job_id = Column(Integer, ForeignKey("import_jobs.id"), nullable=False)
    target_conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    status = Column(String(50), default="pending")

    # Analysis results
    total_messages_in_import = Column(Integer, default=0)
    duplicate_messages = Column(Integer, default=0)
    new_messages = Column(Integer, default=0)
    new_media_files = Column(Integer, default=0)

    # Progress
    processed_messages = Column(Integer, default=0)
    processed_media = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Relationships
    source_import_job = relationship("ImportJob")
    target_conversation = relationship("Conversation")
```

2. **`backend/app/services/merger.py`**
```python
"""
Conversation merge service.

Handles:
- Finding potential merge targets
- Analyzing imports for duplicates
- Executing merge operations
"""

class MergerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = WhatsAppParser()
        self.storage = StorageService()

    async def find_merge_targets(self, conversation_name: str) -> list[Conversation]:
        """Find existing conversations that could be merge targets."""
        pass

    async def analyze_merge(
        self,
        import_job_id: int,
        target_conversation_id: int
    ) -> MergeJob:
        """Analyze an import against an existing conversation."""
        pass

    async def execute_merge(self, merge_job_id: int) -> MergeJob:
        """Execute the merge operation."""
        pass

    def _generate_content_hash(self, message: ParsedMessage) -> str:
        """Generate hash for duplicate detection."""
        pass

    async def _get_existing_hashes(self, conversation_id: int) -> set[str]:
        """Get all content hashes for an existing conversation."""
        pass
```

3. **`backend/app/api/merge.py`**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.merger import MergerService
from ..schemas.merge import (
    MergeAnalyzeRequest,
    MergeAnalyzeResponse,
    MergeExecuteRequest,
    MergeProgressResponse,
)

router = APIRouter()

@router.post("/analyze")
async def analyze_for_merge(...):
    """Analyze uploaded file and find potential merge targets."""
    pass

@router.post("/merge/analyze")
async def analyze_merge(...):
    """Analyze specific merge operation."""
    pass

@router.post("/merge/execute")
async def execute_merge(...):
    """Execute merge operation."""
    pass

@router.get("/merge/progress/{merge_job_id}")
async def get_merge_progress(...):
    """Get merge progress."""
    pass
```

4. **`backend/app/schemas/merge.py`**
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MergeTarget(BaseModel):
    id: int
    name: str
    message_count: int
    last_message_at: Optional[datetime]
    similarity_score: float


class AnalyzeResponse(BaseModel):
    job_id: int
    detected_conversation_name: str
    potential_merge_targets: list[MergeTarget]


class MergeAnalysis(BaseModel):
    merge_job_id: int
    status: str
    total_messages_in_import: int
    duplicate_messages: int
    new_messages: int
    new_media_files: int
    new_participants: list[str]


class MergeProgress(BaseModel):
    merge_job_id: int
    status: str
    progress_percent: float
    new_messages: int
    processed_messages: int
    new_media_files: int
    processed_media: int
```

### 3.6 Frontend Implementation

#### Modified Files:

1. **`frontend/src/components/import/ImportDialog.tsx`**

Add new steps to the import flow:
```typescript
type ImportStep =
  | 'upload'
  | 'analyzing'      // NEW: Analyzing for merge targets
  | 'merge-choice'   // NEW: User chooses merge or new
  | 'merge-analysis' // NEW: Showing merge analysis
  | 'progress'
  | 'complete'
  | 'error'
```

2. **`frontend/src/components/import/MergeChoice.tsx`** (NEW)
```typescript
interface MergeChoiceProps {
  conversationName: string
  mergeTargets: MergeTarget[]
  onSelectMerge: (targetId: number) => void
  onCreateNew: () => void
}

export default function MergeChoice({ ... }: MergeChoiceProps) {
  // Render list of potential merge targets
  // Each with name, message count, last message date
  // "Merge into this" button for each
  // "Create as new conversation" button at bottom
}
```

3. **`frontend/src/components/import/MergeAnalysis.tsx`** (NEW)
```typescript
interface MergeAnalysisProps {
  analysis: MergeAnalysisData
  onConfirm: () => void
  onCancel: () => void
}

export default function MergeAnalysis({ ... }: MergeAnalysisProps) {
  // Show:
  // - Total messages in import
  // - Already in archive (duplicates)
  // - New messages to add
  // - New media files
  // - New participants (if any)
  // Confirm / Cancel buttons
}
```

4. **`frontend/src/api/client.ts`**

Add new API functions:
```typescript
export const analyzeImport = async (jobId: number): Promise<AnalyzeResponse> => {
  const { data } = await api.post('/import/analyze', { job_id: jobId })
  return data
}

export const analyzeMerge = async (
  jobId: number,
  targetConversationId: number
): Promise<MergeAnalysis> => {
  const { data } = await api.post('/import/merge/analyze', {
    job_id: jobId,
    target_conversation_id: targetConversationId
  })
  return data
}

export const executeMerge = async (mergeJobId: number): Promise<{ status: string }> => {
  const { data } = await api.post('/import/merge/execute', {
    merge_job_id: mergeJobId
  })
  return data
}

export const getMergeProgress = async (mergeJobId: number): Promise<MergeProgress> => {
  const { data } = await api.get(`/import/merge/progress/${mergeJobId}`)
  return data
}
```

---

## 4. Edge Cases & Considerations

### 4.1 Time Zone Handling
WhatsApp exports use the device's local time. If a user exports from different devices with different time zones, the same message could have different timestamps.

**Solution:** Round timestamps to the nearest minute and use content matching as a secondary check.

### 4.2 Edited Messages
WhatsApp allows editing messages. An edited message will have different content but the same timestamp/sender.

**Solution:**
- Use timestamp + sender as primary key
- If same timestamp/sender but different content, keep BOTH (mark as potential edit)
- Or: prefer the newer import's version (configurable)

### 4.3 Deleted Messages
Messages deleted in WhatsApp won't appear in newer exports.

**Solution:** Never delete messages from archive during merge. Only ADD new messages.

### 4.4 Media File Handling
Same media file might be exported with different filenames.

**Solution:**
- Generate hash of media content (first 1KB + file size)
- Skip duplicate media uploads
- Link new messages to existing media if content matches

### 4.5 Conversation Name Changes
Group names can change over time.

**Solution:**
- Use fuzzy matching for conversation names
- Show similarity score to user
- Allow manual selection of merge target

### 4.6 Large Conversations
Conversations with 100K+ messages need efficient duplicate checking.

**Solution:**
- Use database index on content_hash
- Batch hash lookups (1000 at a time)
- Use SET operations for duplicate detection
- Stream processing for memory efficiency

### 4.7 Participant Changes
New participants may join the group in the newer export.

**Solution:**
- Detect new sender names
- Create new Participant records
- Assign new colors that don't conflict with existing

---

## 5. Database Migration

```python
"""Add merge support

Revision ID: 002_add_merge_support
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Add content_hash to messages
    op.add_column('messages',
        sa.Column('content_hash', sa.String(32), nullable=True)
    )
    op.create_index(
        'ix_messages_conversation_content_hash',
        'messages',
        ['conversation_id', 'content_hash']
    )

    # Create merge_jobs table
    op.create_table(
        'merge_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_import_job_id', sa.Integer(),
                  sa.ForeignKey('import_jobs.id'), nullable=False),
        sa.Column('target_conversation_id', sa.Integer(),
                  sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('total_messages_in_import', sa.Integer(), default=0),
        sa.Column('duplicate_messages', sa.Integer(), default=0),
        sa.Column('new_messages', sa.Integer(), default=0),
        sa.Column('new_media_files', sa.Integer(), default=0),
        sa.Column('processed_messages', sa.Integer(), default=0),
        sa.Column('processed_media', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table('merge_jobs')
    op.drop_index('ix_messages_conversation_content_hash')
    op.drop_column('messages', 'content_hash')
```

---

## 6. Testing Plan

### 6.1 Unit Tests

```python
# test_merger.py

class TestContentHash:
    def test_same_message_same_hash(self):
        """Identical messages should produce identical hashes."""
        pass

    def test_different_timestamp_different_hash(self):
        """Messages with different timestamps should have different hashes."""
        pass

    def test_minor_time_difference_same_hash(self):
        """Messages within same minute should have same hash."""
        pass

    def test_case_insensitive_sender(self):
        """Sender name matching should be case-insensitive."""
        pass


class TestMergeAnalysis:
    def test_find_all_duplicates(self):
        """Should correctly identify all duplicate messages."""
        pass

    def test_find_all_new_messages(self):
        """Should correctly identify all new messages."""
        pass

    def test_empty_overlap(self):
        """Handle case where imports have no overlap."""
        pass

    def test_complete_overlap(self):
        """Handle case where import is subset of existing."""
        pass


class TestMergeExecution:
    def test_inserts_only_new_messages(self):
        """Should only insert messages not already in conversation."""
        pass

    def test_updates_conversation_metadata(self):
        """Should update message_count, first/last_message_at."""
        pass

    def test_handles_new_participants(self):
        """Should create new participant records."""
        pass

    def test_updates_search_vectors(self):
        """Should update search vectors for new messages."""
        pass
```

### 6.2 Integration Tests

```python
# test_merge_flow.py

class TestMergeFlow:
    async def test_full_merge_flow(self):
        """Test complete merge flow from upload to completion."""
        # 1. Import initial conversation
        # 2. Upload second export
        # 3. Analyze and find merge target
        # 4. Analyze merge
        # 5. Execute merge
        # 6. Verify final state
        pass

    async def test_merge_with_media(self):
        """Test merge correctly handles media files."""
        pass

    async def test_concurrent_merge_prevention(self):
        """Prevent concurrent merges to same conversation."""
        pass
```

### 6.3 Manual Test Cases

| # | Test Case | Steps | Expected Result |
|---|-----------|-------|-----------------|
| 1 | Basic merge | Import chat, wait 1 month, import again | Only new messages added |
| 2 | No overlap | Import Jan-Jun, then Jul-Dec separately | Both ranges present, no duplicates |
| 3 | Complete duplicate | Import same file twice | 0 new messages, merge completes |
| 4 | New participant | Add person to group, export again | New participant created, messages linked |
| 5 | Media merge | Import with media, then again with new media | New media uploaded, old media preserved |
| 6 | Large conversation | Merge into 100K+ message conversation | Completes within reasonable time (<5 min) |

---

## 7. Rollout Plan

### Phase 1: Backend Foundation (Day 1)
- [ ] Add `content_hash` column to messages table
- [ ] Create `merge_jobs` table
- [ ] Implement `MergerService` with hash generation
- [ ] Backfill `content_hash` for existing messages (migration script)

### Phase 2: Merge Analysis (Day 1-2)
- [ ] Implement merge target detection
- [ ] Implement merge analysis endpoint
- [ ] Add merge-related API endpoints
- [ ] Write unit tests for analysis

### Phase 3: Merge Execution (Day 2)
- [ ] Implement merge execution logic
- [ ] Handle media file merging
- [ ] Update search vectors
- [ ] Write integration tests

### Phase 4: Frontend Integration (Day 2-3)
- [ ] Add merge choice dialog
- [ ] Add merge analysis preview
- [ ] Update import progress flow
- [ ] Handle merge progress polling

### Phase 5: Testing & Polish (Day 3)
- [ ] End-to-end testing
- [ ] Performance testing with large conversations
- [ ] Error handling improvements
- [ ] Documentation updates

---

## 8. Future Enhancements

### 8.1 Automatic Merge Suggestion
When user imports a file, automatically suggest merging if a matching conversation exists (no need to ask).

### 8.2 Scheduled Imports
Allow users to set up automatic periodic imports from cloud storage (Google Drive, iCloud, etc.).

### 8.3 Conflict Resolution UI
Show side-by-side comparison when messages have same timestamp but different content.

### 8.4 Merge History
Track all merges with ability to "undo" a merge by removing messages added in that merge.

### 8.5 Cross-Platform Support
Support merging exports from different platforms (iOS vs Android WhatsApp exports have slightly different formats).

---

## 9. References

- [WhatsApp Export Format Documentation](./WHATSAPP-EXPORT-FORMAT.md)
- [Current Parser Implementation](../backend/app/services/parser.py)
- [Database Schema](../backend/app/models/)

---

## Appendix A: WhatsApp Export Variations

### iOS Format
```
[DD/MM/YYYY, HH:MM:SS] Sender Name: Message content
```

### Android Format
```
DD/MM/YYYY, HH:MM - Sender Name: Message content
```

### German Locale
```
[DD.MM.YYYY, HH:MM:SS] Sender Name: Message content
```

The parser already handles these variations. The merge feature inherits this support.

---

## Appendix B: Performance Benchmarks

Target performance for merge operations:

| Conversation Size | Analysis Time | Merge Time |
|-------------------|---------------|------------|
| 10,000 messages   | < 5 seconds   | < 30 seconds |
| 50,000 messages   | < 15 seconds  | < 2 minutes |
| 100,000 messages  | < 30 seconds  | < 5 minutes |
| 500,000 messages  | < 2 minutes   | < 15 minutes |

These targets assume PostgreSQL with proper indexing on `content_hash`.
