# Marketing AI

AI-Powered Competitor Ad Analysis & Content Recommendation System

## Overview

This system automatically:
- Discovers and tracks competitors
- Retrieves ads from Meta Ad Library
- Downloads and stores ad creatives (images/videos)
- Analyzes ads using vision AI (GPT-4 Vision for images, Gemini for videos)
- Generates detailed, actionable content recommendations

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: PostgreSQL (Supabase)
- **Storage**: Supabase Storage
- **Task Queue**: Celery + Redis
- **AI Services**: OpenAI GPT-4 Vision, Google Gemini 1.5 Pro, Anthropic Claude

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry
- Docker (for Redis)
- Supabase account
- API keys for: OpenAI, Google AI, Anthropic, Meta

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd marketing-ai

# Install dependencies
make install

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start Redis
make docker-up

# Run database migrations
make migrate

# Start the development server
make dev
```

### Running the Full Stack

In separate terminal windows:

```bash
# Terminal 1: API Server
make dev

# Terminal 2: Celery Worker
make celery-worker

# Terminal 3: Celery Beat (scheduler)
make celery-beat

# Optional - Terminal 4: Celery Flower (monitoring)
make celery-flower
```

## API Endpoints

### Strategy Management
- `POST /api/strategy/upload` - Upload PDF and extract strategy
- `POST /api/strategy` - Create strategy manually
- `GET /api/strategy/{id}` - Get strategy by ID
- `PUT /api/strategy/{id}` - Update strategy
- `DELETE /api/strategy/{id}` - Delete strategy
- `GET /api/strategy` - List all strategies

### Competitor Management
- `GET /api/competitors` - List all competitors
- `POST /api/competitors/add` - Manually add competitor
- `GET /api/competitors/{id}` - Get competitor by ID
- `PUT /api/competitors/{id}` - Update competitor
- `DELETE /api/competitors/{id}` - Deactivate competitor
- `POST /api/competitors/discover` - Auto-discover competitors

### Ad Management
- `GET /api/ads` - List ads (with filtering)
- `GET /api/ads/{id}` - Get single ad with analysis
- `GET /api/ads/stats` - Get ad statistics
- `POST /api/ads/retrieve` - Retrieve ads for competitor
- `POST /api/ads/analyze/{id}` - Analyze single ad
- `POST /api/ads/analyze/run` - Run batch analysis

### Recommendations
- `POST /api/recommendations/generate` - Generate new recommendations
- `GET /api/recommendations/latest` - Get latest recommendation
- `GET /api/recommendations/{id}` - Get specific recommendation
- `GET /api/recommendations` - List all recommendations

## Configuration

### Environment Variables

```bash
# Database (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
DATABASE_URL=postgresql+asyncpg://...

# AI Services
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...

# Meta Ad Library
META_ACCESS_TOKEN=...

# Celery / Redis
REDIS_URL=redis://localhost:6379/0

# App Config
RECOMMENDATION_MODEL=claude  # or "openai"
TOP_N_ADS_FOR_RECOMMENDATIONS=10
```

### Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| Competitor Discovery | Monthly (1st, 2am) | Find new competitors |
| Ad Retrieval | Weekly (Monday, 3am) | Fetch new ads from all competitors |
| Ad Analysis | Daily (4am) | Analyze pending ads |

## Development

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format
```

### Database Migrations

```bash
# Run migrations
make migrate

# Create new migration
make migrate-new MSG="add new field"

# Rollback
make migrate-rollback
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   FastAPI       │     │   Celery        │
│   REST API      │     │   Workers       │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────┴────┐           ┌──────┴──────┐
    │PostgreSQL│           │    Redis    │
    │(Supabase)│           │             │
    └─────────┘           └─────────────┘
         │
    ┌────┴────┐
    │Supabase │
    │ Storage │
    └─────────┘

External Services:
- Meta Ad Library API
- OpenAI GPT-4 Vision
- Google Gemini 1.5 Pro
- Anthropic Claude
```

## Workflow

1. **Strategy Ingestion**: Upload PDF → AI extracts structured data
2. **Competitor Discovery**: AI researches and identifies competitors (monthly)
3. **Ad Retrieval**: Fetch ads from Meta Ad Library (weekly)
4. **Creative Download**: Store images/videos in Supabase Storage
5. **Ad Analysis**: GPT-4 Vision (images) / Gemini (videos) analyze effectiveness
6. **Recommendation Generation**: Claude/GPT-4 generates detailed content plans

## License

MIT
