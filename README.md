# PackagePro Estimator

Intelligent cost estimation platform for bespoke packaging manufacturers.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Start PostgreSQL
docker-compose up db -d

# Run migrations
alembic upgrade head

# Start server
uvicorn backend.app.main:app --reload
```

## API Documentation

Visit http://localhost:8000/api/docs for interactive API documentation.

## Features

- Dimension-based cost estimation
- Material price management with CSV import
- Production feedback collection for ML training
- Confidence intervals on estimates
