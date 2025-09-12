# Libro Bible API

A Flask-based REST API for a Bible reader application with AI-powered theological analysis from multiple denominational perspectives.

## Features

- **Bible Text Access**: Complete Bible text with search and reference lookup
- **AI Theological Analysis**: Multi-perspective analysis using Google's Gemini AI
  - Catholic, Orthodox (Eastern, Oriental, Church of the East)
  - Protestant (Lutheran, Reformed/Calvinist, Baptist, Methodist, Pentecostal, Anglican, Presbyterian)
- **Smart Caching**: AI summaries are globally cached to reduce API costs
- **Cross-References**: AI-generated cross-references with relevance explanations
- **Strong's Concordance**: Hebrew/Greek word analysis and concordance lookup

## Tech Stack

- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **AI**: Google Gemini 2.5 Flash with structured output
- **Database**: PostgreSQL with Flask-Migrate

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL database
- Google AI Studio API key

### Installation

1. Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```env
GOOGLE_AI_STUDIO_API_KEY=your_api_key_here
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=libros
POSTGRES_HOST=your_host
POSTGRES_PORT=5432
```

3. Initialize the database:
```bash
python3 setup_db.py
flask db upgrade
```

4. Import sample Bible data:
```bash
python3 import_bible_data.py --sample
```

5. Start the server:
```bash
python3 app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Bible Content
- `GET /api/bible/books` - List all books
- `GET /api/bible/books/{id}` - Get specific book with chapters
- `GET /api/bible/chapters/{id}/verses` - Get all verses in a chapter
- `GET /api/bible/verses/{id}` - Get specific verse
- `GET /api/bible/verses/range?start={id}&end={id}` - Get verse range
- `GET /api/bible/search?q={query}` - Search verses
- `GET /api/bible/reference?ref={reference}` - Get verses by reference (e.g., "John 3:16")

### AI Analysis
- `POST /api/analysis/summary` - Generate theological summary
- `POST /api/analysis/question` - Ask specific questions about verses
- `GET /api/analysis/history` - Get user's analysis history
- `GET /api/analysis/history/{id}` - Get specific analysis details

### Strong's Concordance
- `GET /api/strongs/lookup/{strongs_number}` - Get Strong's entry details
- `GET /api/strongs/search?q={query}` - Search Strong's entries
- `GET /api/strongs/concordance/{strongs_number}` - Get verse concordance for Strong's number
- `GET /api/strongs/verse/{verse_id}/strongs` - Get Strong's numbers for a verse

## Example Usage

### 1. Get Bible Text
```bash
# Get John 3:16
curl -X GET "http://localhost:5000/api/bible/reference?ref=John 3:16"
```

### 2. Generate AI Analysis
```bash
# Get theological summary for John 3:16
curl -X POST http://localhost:5000/api/analysis/summary \
  -H "Content-Type: application/json" \
  -d '{
    "verse_range_start": 1,
    "verse_range_end": 1,
    "perspectives": ["catholic", "lutheran", "baptist"]
  }'
```

### 3. Ask Specific Questions
```bash
# Ask a question about John 3:16
curl -X POST http://localhost:5000/api/analysis/question \
  -H "Content-Type: application/json" \
  -d '{
    "verse_range_start": 1,
    "question": "What does this verse teach about salvation?",
    "perspectives": ["catholic", "reformed_calvinist"]
  }'
```

## Database Schema

### Core Tables
- **books**: Bible books (66 total)
- **chapters**: Bible chapters
- **verses**: Individual verses with text
- **verse_summaries**: Cached AI summaries (global)
- **search_cache**: Cached search results
- **strongs_entries**: Strong's concordance entries
- **verse_strongs_mappings**: Verse to Strong's number mappings

## AI Integration

The system uses Google's Gemini 2.5 Flash model with structured output to ensure consistent, parseable responses. Each theological perspective has customized system prompts that emphasize the distinctive doctrines and interpretive approaches of that tradition.

### Supported Perspectives
- **Catholic**: Tradition, Magisterium, Sacraments
- **Eastern Orthodox**: Theosis, Patristics, Liturgy
- **Oriental Orthodox**: Miaphysite Christology, Ancient traditions
- **Church of the East**: Dyophysite Christology, Syriac tradition
- **Lutheran**: Sola fide, Sola scriptura, Law/Gospel
- **Reformed/Calvinist**: Sovereignty of God, Predestination, Covenant theology
- **Baptist**: Believer's baptism, Congregational governance, Soul liberty
- **Methodist**: Prevenient grace, Holiness, Social justice
- **Pentecostal**: Spirit baptism, Gifts of the Spirit, Divine healing
- **Anglican**: Via media, Book of Common Prayer, Episcopal polity
- **Presbyterian**: Westminster standards, Presbyterian polity, Reformed theology

## Development

### Adding New Bible Books
Use the import script to add more biblical content:
```bash
python3 import_bible_data.py --books  # Creates all 66 book records
```

### Database Migrations
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

### Testing
The API includes sample data (John 3:16-17, Romans 3:23-24, Genesis 1:1-3) for testing all functionality.

## Future Enhancements

- Complete ESV Bible text import
- Additional Bible translations
- Enhanced search capabilities
- Mobile app support
- Verse highlighting and bookmarking
- Social sharing of analyses

## License

This project is for educational and personal use.
