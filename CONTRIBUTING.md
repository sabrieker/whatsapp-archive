# Contributing to WhatsApp Archive Viewer

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions. We're building something useful together.

## Getting Started

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/sabrieker/whatsapp-archive.git
   cd whatsapp-archive
   ```

2. **Set up services:**
   - PostgreSQL (default port 5432)
   - MinIO (default port 9000)

3. **Create your config file:**
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

4. **Initialize the project:**
   ```bash
   python start.py init
   ```
   This will:
   - Create a Python virtual environment
   - Install backend dependencies
   - Install frontend dependencies
   - Create database tables

5. **Run the development servers:**
   ```bash
   python start.py dev
   ```
   This starts both backend (port 8000) and frontend (port 5173).

   Or run them separately:
   ```bash
   python start.py backend   # Terminal 1
   python start.py frontend  # Terminal 2
   ```

6. **Verify everything works:**
   ```bash
   python start.py check
   ```

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](../../issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - Environment details (OS, browser, Python version)

### Suggesting Features

1. Check existing [Issues](../../issues) for similar suggestions
2. Create a new issue with the `enhancement` label
3. Describe the feature and its use case
4. Explain why it would benefit users

### Submitting Code

1. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Make your changes:**
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation if needed

3. **Test your changes:**
   - Ensure the app runs without errors
   - Test the feature/fix manually
   - Add tests if applicable

4. **Commit your changes:**
   ```bash
   git commit -m "Add feature: description"
   # or
   git commit -m "Fix: description of the fix"
   ```

5. **Push and create a PR:**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a Pull Request on GitHub.

## Code Style

### Python (Backend)

- Use type hints where possible
- Follow PEP 8 guidelines
- Use async/await for database operations
- Keep functions focused and small

```python
# Good
async def get_conversation(db: AsyncSession, conversation_id: int) -> Conversation:
    """Fetch a conversation by ID."""
    return await db.get(Conversation, conversation_id)

# Avoid
def get_conversation(db, id):
    return db.get(Conversation, id)
```

### TypeScript (Frontend)

- Use TypeScript interfaces for all data structures
- Use functional components with hooks
- Keep components focused and reusable

```typescript
// Good
interface MessageProps {
  message: Message;
  isGrouped: boolean;
}

function MessageBubble({ message, isGrouped }: MessageProps) {
  // ...
}

// Avoid
function MessageBubble(props: any) {
  // ...
}
```

### CSS/Styling

- Use TailwindCSS utility classes
- Follow existing naming patterns
- Keep responsive design in mind

## Project Structure

```
backend/
├── app/
│   ├── api/          # Route handlers
│   ├── models/       # Database models
│   ├── schemas/      # Request/response schemas
│   └── services/     # Business logic

frontend/
├── src/
│   ├── api/          # API client
│   ├── components/   # Reusable components
│   ├── pages/        # Page components
│   └── hooks/        # Custom hooks
```

## Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Update the README if adding new features
- Include screenshots for UI changes
- Reference related issues
- Respond to review feedback promptly

## Questions?

Feel free to open an issue with the `question` label or reach out to the maintainers.

Thank you for contributing!
