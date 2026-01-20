# Council Assistant

A semantic search tool for Kent County Council records, providing AI-powered search capabilities across thousands of council meetings, agenda items, and documents.

## Overview

Council Assistant is a comprehensive data pipeline and search application that scrapes, processes, and indexes Kent County Council records, making them searchable through a Streamlit web interface. The system combines web scraping, natural language processing, vector embeddings, and AI analysis to help users find relevant information across years of council records.

## Project History

### Timeline

**May 14, 2025** - Project inception
- Fresh repository created
- Initial web scraping notebooks developed for KCC TV councillor profiles
- Candidate information scraping from "Who Can I Vote For"
- Minutes of Meeting (MoM) summarization prompts created

**May 15-16, 2025** - Data processing infrastructure
- Voting records parsing functionality
- OpenAI batch processing for meeting summarization
- Semantic chunking of minutes
- Metadata enrichment and NLP extraction experiments
- Agenda and meeting metadata separation

**May 17-18, 2025** - Scraper development
- Meetings scraper refined and tested
- Committee metadata extraction from web pages
- Borough scraping drafts
- Scraping notebooks organized and renamed

**May 19-20, 2025** - Core infrastructure
- Main scraper with throttling to avoid detection
- PDF processing unit scaffolded (scrape, classify, process, summarize)
- Committee assignment logic debugged
- Workflow shifted from document-centric to meetings-first approach

**May 21-22, 2025** - Search system development
- PDF scraping and summarization scripts refined
- Agenda item junk detection and filtering
- Embedding scripts separated (PDF chunks vs agenda items)
- Question parsing from documents

**May 23-24, 2025** - Application development
- New search page created in Streamlit app
- FAISS index integration
- Claude and DeepSeek assisted with search page refinements
- Election data scraping expanded to all Kent councils

**May 25-28, 2025** - Production preparation & MVP deployment
- README documentation updated
- App pages reorganized
- Modular architecture implemented (search, data, utils modules)
- Comprehensive logging and feedback systems added
- **252MB of council data** added (meetings, documents, search indexes)
- Cloud deployment configuration (dev containers, config files)
- Path handling for both local and cloud deployment
- Repository cleaned of development files
- **May 28, 2025**: Production MVP deployed

**January 20, 2026** - Repository maintenance
- .gitignore updates
- Repository synchronized

## Main Functions

### 1. Web Scraping
**Location**: Scripts and notebooks for data collection

**Capabilities**:
- Scrapes Kent County Council website for meetings, agendas, and documents
- Extracts councillor profiles from KCC TV
- Collects election data from multiple sources
- Implements throttling to avoid detection
- Handles multiple document types (minutes, reports, assessments)

**Key files**:
- Meeting and agenda scrapers
- Committee metadata extraction
- PDF document scrapers
- Election results collectors

### 2. Data Processing
**Location**: `modules/data/`, PDF processor scripts

**Capabilities**:
- Classifies PDFs by type (minutes, reports, EQIA, decisions)
- Summarizes documents using OpenAI GPT models
- Extracts structured metadata (dates, committees, people)
- Semantic chunking of meeting minutes
- Deduplication and cleaning
- Assigns unique document IDs

**Key components**:
- PDF classification and processing
- Metadata enrichment
- Text chunking and deduplication
- Committee and people entity extraction

### 3. Search & Indexing
**Location**: `modules/search/`, `data/embeddings/`

**Capabilities**:
- Generates vector embeddings using OpenAI's text-embedding-3-small model
- Creates FAISS indexes for fast semantic search
- Separate indexes for agenda items and PDF summaries
- Relevance scoring and ranking
- Date-based filtering and sorting

**Key features**:
- Semantic search across ~25M of agenda text
- Document search across ~6.3M of document summaries
- Committee and document type filtering
- Configurable result pagination

### 4. Web Application
**Location**: `streamlit_app.py`, `modules/`

**Capabilities**:
- Streamlit-based search interface
- Three-tab search system:
  - **Meeting Discussions**: Search agenda items from council meetings
  - **Documents & Reports**: Search official documents and PDFs
  - **AI Summary**: Generate AI analysis of search results
- Real-time filters (date range, committee, document type)
- Comprehensive logging system
- User feedback collection
- Performance monitoring

**Technical features**:
- Modular architecture with separate concerns
- Caching for performance optimization
- Path handling for local and cloud deployment
- Integrated logging and error handling

### 5. Logging & Monitoring
**Location**: `modules/utils/`, `logs/`, `log/`

**Capabilities**:
- Search query logging
- Error tracking (JSONL format)
- Performance metrics
- User interaction tracking
- User feedback system
- Application logs

## Data Structure

### Data Location
All data files are stored in `/Users/lgfolder/github/shared_data/councils/council-assistant/data/`

### Metadata Files (`data/metadata/`)
- **agendas.jsonl** (25MB): Individual agenda items from meetings
- **meetings.jsonl** (18MB): Meeting metadata (dates, committees, codes)
- **documents.jsonl** (6.3MB): PDF documents with URLs and metadata
- **pdf_warehouse.jsonl** (20MB): Full PDF text and summaries
- **pdf_meta_warehouse.jsonl** (20MB): PDF processing metadata
- **committees.jsonl** (12KB): Committee information
- **people.jsonl** (598KB): Councillor and people data
- **divisions_metadata.jsonl** (154KB): Electoral division information

### Embeddings (`data/embeddings/`)
- **agendas/**: FAISS index and metadata for agenda item search
- **pdf_summaries/**: FAISS index and metadata for document search

## Technical Stack

### Core Technologies
- **Python 3.x**: Primary programming language
- **Streamlit**: Web application framework
- **OpenAI API**:
  - `text-embedding-3-small` for embeddings
  - `gpt-4o-mini` for AI analysis and summarization
- **FAISS**: Vector similarity search
- **Pandas**: Data manipulation
- **jsonlines**: JSONL file handling

### Additional Libraries
- BeautifulSoup/requests: Web scraping
- NumPy: Numerical operations
- dotenv: Environment variable management

## Architecture

### Modular Design
```
council-assistant/
├── streamlit_app.py          # Main application entry point
├── modules/
│   ├── data/                 # Data loading utilities
│   │   ├── loaders.py        # JSONL loading, caching
│   │   └── __init__.py
│   ├── search/               # Search functionality
│   │   ├── semantic_search.py    # FAISS search, embedding generation
│   │   ├── result_formatters.py  # Result display formatting
│   │   ├── ai_analysis.py        # AI-powered analysis
│   │   └── __init__.py
│   └── utils/                # Utilities
│       ├── logging_system.py     # Comprehensive logging
│       └── feedback_system.py    # User feedback collection
├── data/                     # → Now in shared_data/councils/council-assistant/data/
└── logs/                     # Application logs
```

## Development Approach

### Agile Development
The project was developed in a rapid, iterative manner over approximately 2 weeks (May 14-28, 2025), with clear daily milestones:

1. **Days 1-2**: Foundation (scraping, data collection)
2. **Days 3-4**: Processing pipeline (chunking, embeddings)
3. **Days 5-6**: Infrastructure (scrapers, PDF processing)
4. **Days 7-9**: Search system (FAISS, embeddings)
5. **Days 10-12**: Application (Streamlit, UI)
6. **Days 13-14**: Production (deployment, cleanup)

### Key Design Decisions

**May 18-20**: Workflow pivot from document-centric to meetings-first approach
- Initially focused on processing existing PDF archives
- Shifted to scraping meetings first, then processing associated documents
- This provided better structure and context for document organization

**May 21-23**: Dual-index architecture
- Separate FAISS indexes for agenda items vs PDF summaries
- Allows optimized search strategies for different content types
- Agenda items: Direct text chunks, no need for summarization
- PDFs: Searchable summaries with links to original documents

**May 28**: Modular refactoring for production
- Separated concerns into data, search, and utils modules
- Implemented comprehensive logging and monitoring
- Path abstraction for local and cloud deployment
- Removed all development notebooks and scripts from production

## Usage

### Running Locally
```bash
# Ensure OpenAI API key is set
export OPENAI_API_KEY="your-key-here"

# Run the Streamlit app
streamlit run streamlit_app.py
```

### Configuration
- Data paths automatically handle local vs cloud deployment
- Local: Uses `/Users/lgfolder/github/shared_data/councils/council-assistant/data/`
- Cloud: Uses relative `./data/` path
- Configure via `.streamlit/config.toml`

## Data Statistics

- **Meetings**: ~18MB of meeting metadata
- **Agenda Items**: ~25MB of searchable agenda content
- **Documents**: ~6.3MB of document metadata
- **Total Dataset**: ~241MB including embeddings
- **Date Range**: Multiple years of Kent County Council records

## Features

### Search Capabilities
- Natural language queries
- Semantic similarity matching
- Date range filtering
- Committee filtering
- Document type filtering
- Relevance and date sorting
- Configurable pagination (10/25/50/100 results per page)

### AI Analysis
- Context-aware summarization of search results
- Key findings extraction
- Policy development tracking
- Sources citation

### User Experience
- Clean, intuitive interface
- Three-tab navigation
- Real-time search feedback
- Result highlighting
- Direct links to source documents
- Meeting URLs for context

## Logging & Monitoring

The system tracks:
- All search queries with timestamps
- Performance metrics (query time, result counts)
- User interactions (clicks, feedback)
- Errors with stack traces
- User feedback and ratings

## Future Development

Potential areas for expansion:
- Multi-council support (expand beyond Kent)
- Advanced NLP features (entity recognition, topic modeling)
- User accounts and saved searches
- Email alerts for new relevant documents
- Comparative analysis across councils
- Historical trend visualization

## Credits

Developed by lusavkaedu

Built with assistance from Claude AI (code refinements), DeepSeek (search page development), and OpenAI (embeddings and summarization).

## Repository

GitHub: https://github.com/lusavkaedu/council-assistant

## License

See repository for license information.
