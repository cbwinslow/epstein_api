# OSINT Extraction & Analysis Methodology

## 1. Core Objective
To systematically convert unstructured, multimodal data (PDFs, images, flight logs, court transcripts) into a structured Knowledge Graph and searchable RAG database to map the Epstein network.

## 2. Entity Extraction Rules
The system must aggressively identify and extract the following entities from the processed JSON text:
- **PERSON:** Full names, aliases, or titles (e.g., "Prince Andrew", "Doe 107").
- **ORGANIZATION:** Companies, foundations, shell corporations, legal entities.
- **LOCATION:** Specific addresses, islands, properties, flight destinations.
- **AIRCRAFT:** Tail numbers (e.g., "N228AW", "N120JE").
- **DATE/TIME:** Specific dates or inferred date ranges.
- **EVENT:** Meetings, flights, court depositions, financial transfers.

## 3. Relationship Scoring Rubric (The "Depth" Matrix)
Agents must not just link people; they must weight the connection. Use this 1-10 scale when generating Cypher queries for Neo4j:
- **Level 1-2 (Incidental):** Mentioned in the same document but no direct interaction. Address book entries without context.
- **Level 3-4 (Proximity):** Attended the same large event. Flown on the aircraft but on different dates.
- **Level 5-6 (Direct Contact):** Documented meetings. Flown on the same specific flight. Direct email correspondence.
- **Level 7-8 (Professional/Financial Ties:** Shared board memberships. Direct financial transactions. Legal representation.
- **Level 9-10 (Core Network/Complicity):** Co-defendants. Facilitators. Shared ownership of shell companies. Repeat, high-frequency travel together.

## 4. Timeline Reconstruction
When extracting events, the Timeline Agent must attempt to ground them in absolute time. If a document says "Last Tuesday", the agent must cross-reference the document's metadata (e.g., email sent date) to calculate the exact `YYYY-MM-DD`.
