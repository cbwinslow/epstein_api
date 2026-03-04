# API Documentation

## Base URL
```
http://localhost:8000
```

## OpenAPI Schema
Full schema available at: http://localhost:8000/docs

## Endpoints

### Health Check

#### GET /health
Check if the API is running.

**Response:**
```json
{
  "status": "healthy"
}
```

#### GET /
Get API information.

**Response:**
```json
{
  "name": "Epstein OSINT Pipeline",
  "version": "0.1.0",
  "status": "running"
}
```

---

### Ingestion API

#### POST /api/ingest/url
Add a single URL to the download queue.

**Request Body:**
```json
{
  "url": "https://example.com/document.pdf"
}
```

**Response:**
```json
{
  "url": "https://example.com/document.pdf",
  "status": "PENDING",
  "dest_path": "/data/downloads/file_12345_document.pdf"
}
```

#### POST /api/ingest/urls
Add multiple URLs to the download queue.

**Request Body:**
```json
{
  "urls": [
    "https://example.com/doc1.pdf",
    "https://example.com/doc2.pdf"
  ]
}
```

**Response:**
```json
[
  {
    "url": "https://example.com/doc1.pdf",
    "status": "PENDING",
    "dest_path": "/data/downloads/file_123_doc1.pdf"
  },
  {
    "url": "https://example.com/doc2.pdf",
    "status": "PENDING",
    "dest_path": "/data/downloads/file_456_doc2.pdf"
  }
]
```

#### GET /api/ingest/tasks
List all download tasks.

**Query Parameters:**
- `status` (optional): Filter by status (PENDING, DOWNLOADING, COMPLETED, FAILED)
- `limit` (optional): Maximum number of tasks to return (default: 100)

**Response:**
```json
{
  "total": 2,
  "tasks": [
    {
      "url": "https://example.com/doc.pdf",
      "status": "COMPLETED",
      "dest_path": "/data/downloads/file_123_doc.pdf",
      "retries": 0,
      "error_message": null
    }
  ]
}
```

#### POST /api/ingest/status
Update a task's status (for testing).

**Request Body:**
```json
{
  "url": "https://example.com/doc.pdf",
  "status": "COMPLETED"
}
```

---

### Graph API

#### GET /api/graph/network
Get network graph data for visualization.

**Query Parameters:**
- `limit` (optional): Maximum nodes to return (default: 500, range: 10-2000)
- `min_score` (optional): Minimum relationship score (default: 1, range: 1-10)

**Response:**
```json
{
  "nodes": [
    {
      "id": 1,
      "label": "Person",
      "name": "John Doe"
    }
  ],
  "links": [
    {
      "source": 1,
      "target": 2,
      "type": "FLEW_WITH",
      "depth_score": 7
    }
  ]
}
```

#### GET /api/graph/node/{node_name}
Get detailed information about a specific node.

**Response:**
```json
{
  "n": {"name": "John Doe", "aliases": ["JD"]},
  "outgoing": [
    {
      "target": "Jane Doe",
      "type": "FLEW_WITH",
      "score": 5,
      "evidence": ["Flight log 2020-01-15"]
    }
  ]
}
```

#### GET /api/graph/stats
Get graph statistics.

**Response:**
```json
{
  "Person": 150,
  "Organization": 45,
  "Location": 30,
  "Aircraft": 12,
  "Event": 75
}
```

---

## Status Codes

| Code | Description |
|------|-------------|
| 200 | OK |
| 201 | Created |
| 400 | Bad Request |
| 404 | Not Found |
| 500 | Internal Server Error |

## Error Response Format

```json
{
  "detail": "Error message here"
}
```
