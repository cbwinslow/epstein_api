# User Guide

## Overview

The Epstein OSINT Pipeline is a document analysis platform for processing unstructured documents and building a knowledge graph. This guide covers how to use the web interface.

## Accessing the Application

Open your browser and navigate to:
```
http://localhost:3000
```

## The UI Funnel

The application is organized into four main sections:

---

### 1. Ingest (/ingest)

Add document URLs to the processing queue.

**How to use:**
1. Navigate to the Ingest page
2. Paste URL(s) into the text box (bulk paste supported)
3. Click "Add URLs" to queue them
4. Monitor progress with real-time status updates

**Status values:**
- `PENDING` - Queued for download
- `DOWNLOADING` - Currently downloading
- `COMPLETED` - Successfully downloaded
- `FAILED` - Download failed

---

### 2. Processing Queue (/process)

Monitor the ETL pipeline for document processing.

**How to use:**
1. Navigate to the Process page
2. View pending/processing/completed/failed counts
3. Click on individual files to see processing details
4. Use "Force OCR" to retry failed files with OCR

**Processing methods:**
- `PyMuPDF` - Native PDF text extraction
- `Tesseract_OCR` - OCR for scanned documents
- `Surya_OCR` - Advanced OCR with layout analysis

---

### 3. Analysis & Knowledge Graph (/analyze)

Visualize and explore the extracted network.

**How to use:**
1. Navigate to the Analyze page
2. View the interactive network graph
3. Nodes are colored by entity type:
   - 🔵 Person
   - 🟢 Organization  
   - 🟡 Location
   - 🔴 Aircraft
   - 🟣 Event
4. Click nodes to see details
5. Links show relationship strength (thickness = depth score)

**Relationship depth scores:**
- 1-2: Incidental (same document)
- 3-4: Proximity (same event, different dates)
- 5-6: Direct Contact (documented meetings)
- 7-8: Professional/Financial ties
- 9-10: Core Network (co-defendants, facilitators)

---

### 4. Settings (/settings)

Configure system behavior.

**Available settings:**
- OpenRouter API key configuration
- Ollama model selection
- Download concurrency limits
- Worker settings

---

## API Usage

You can also interact with the system via the REST API:

### Add a URL
```bash
curl -X POST http://localhost:8000/api/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/doc.pdf"}'
```

### Check Tasks
```bash
curl http://localhost:8000/api/ingest/tasks
```

### View Graph Stats
```bash
curl http://localhost:8000/api/graph/stats
```

---

## Troubleshooting

### Container Issues
```bash
# View all logs
docker compose logs -f

# Check container status
docker compose ps

# Restart a service
docker compose restart worker
```

### Common Issues

1. **Worker not connecting to Redis**
   - Check that Redis container is running: `docker ps | grep redis`
   - Verify Redis URL in config

2. **Neo4j connection refused**
   - Wait for Neo4j to initialize (first start takes ~30s)
   - Check credentials in config

3. **Download fails**
   - Check network connectivity
   - Verify URL is accessible
   - Check worker logs for errors

---

## Best Practices

1. **Start small** - Test with a few documents first
2. **Monitor logs** - Watch worker logs for processing errors
3. **Check graph** - Verify entities are being extracted correctly
4. **Review relationships** - Ensure relationship scores make sense
