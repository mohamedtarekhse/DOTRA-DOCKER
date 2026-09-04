# Feature Specification: Seed Data & End-to-End Testing

**Feature Branch**: `001-seed-data-e2e-testing`

**Created**: 2026-09-04

**Status**: Draft

**Input**: User description: "I NEED THE APP TO HAVE SEED DATA AND TEST THEM BY REAL CASES TO CHECK ALL FUNCTIONALITY EVEN BACKEND AND FRONTEND"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Realistic Seed Data Population (Priority: P1)

As a system administrator, I want the application to be pre-populated with realistic factory/warehouse surveillance data so that I can immediately evaluate the system's capabilities without manually creating hundreds of records.

The seed data must cover all entity types in the system: cameras of every type (LPR, CCTV, PTZ), registered vehicles with different statuses, authorized personnel across departments, and a library of captured images with AI-generated embeddings (CLIP vectors, face embeddings, YOLO detections). This data should represent a realistic factory environment with multiple gates, loading docks, restricted zones, and parking areas.

**Why this priority**: Without seed data, the application appears empty and non-functional. All downstream testing and demonstration depends on having data to work with.

**Independent Test**: Can be verified by querying each entity type and confirming records exist with correct attributes, relationships, and AI embeddings stored in the vector database.

**Acceptance Scenarios**:

1. **Given** a fresh database deployment, **When** the seed process completes, **Then** at least 10 cameras exist covering all three types (LPR, CCTV, PTZ) distributed across factory zones
2. **Given** a fresh database deployment, **When** the seed process completes, **Then** at least 4 vehicles exist with different plate numbers, types (car/truck), and whitelisting statuses
3. **Given** a fresh database deployment, **When** the seed process completes, **Then** at least 3 persons exist across different departments with assigned access levels
4. **Given** a fresh database deployment, **When** the seed process completes, **Then** at least 10 images exist in the image store with valid CLIP embeddings (512-dimensional vectors) stored in the vector database
5. **Given** seeded images, **When** a text search is performed, **Then** relevant results are returned with similarity scores above a meaningful threshold

---

### User Story 2 - Backend API Functional Verification (Priority: P1)

As a quality assurance engineer, I want every backend API endpoint to be tested against real data so that I can confirm the entire API layer works correctly end-to-end.

Tests must exercise the complete lifecycle of each resource: authentication, CRUD operations, business logic flows (gate LPR events, exit approvals, manual overrides), alerts, permits, search, and WebSocket connectivity. Each test must use realistic payloads and verify both success paths and error handling.

**Why this priority**: Backend correctness is foundational — if the API layer is broken, the entire system is non-functional regardless of UI quality.

**Independent Test**: Can be run as a standalone automated test suite that produces a pass/fail report for every API endpoint.

**Acceptance Scenarios**:

1. **Given** valid admin credentials, **When** the login endpoint is called, **Then** a JWT token is returned and subsequent authenticated requests succeed
2. **Given** an authenticated session, **When** a vehicle is created, retrieved, updated, and deleted, **Then** all CRUD operations complete successfully with correct data
3. **Given** a registered whitelisted vehicle, **When** an LPR gate event occurs, **Then** the system processes the event and makes an entry decision
4. **Given** a vehicle requiring exit permission, **When** a manager approves the exit, **Then** the gate opens and the exit is recorded
5. **Given** an intrusion alert is triggered, **When** it is created and resolved, **Then** the full alert lifecycle completes with correct status transitions
6. **Given** seeded images with embeddings, **When** a text-to-image search is performed via the API, **Then** matching images are returned ranked by similarity score
7. **Given** any protected endpoint, **When** accessed without authentication, **Then** a 401 or 403 response is returned

---

### User Story 3 - Frontend Dashboard Verification (Priority: P2)

As a factory security operator, I want to verify that every page of the web dashboard loads correctly, displays data properly, and responds to user interactions so that I can trust the system for daily operations.

Each page — dashboard overview, vehicles, persons, gates, alerts, pre-approvals, settings, and search — must render without errors, display seeded data in tables/lists, and support key interactions (forms, buttons, navigation). The Fiori-themed UI must be visually consistent across all pages.

**Why this priority**: The dashboard is the primary user interface — even if the backend is perfect, a broken or empty-looking UI makes the system unusable for operators.

**Independent Test**: Can be tested by navigating to each page and verifying it loads (HTTP 200), contains expected content, and redirects unauthenticated users to login.

**Acceptance Scenarios**:

1. **Given** an unauthenticated browser session, **When** any protected page is accessed, **Then** the user is redirected to the login page
2. **Given** valid login credentials, **When** the user submits the login form, **Then** they receive an auth cookie and are redirected to the dashboard
3. **Given** an authenticated session, **When** the dashboard page loads, **Then** it displays summary tiles showing counts for cameras, vehicles, persons, and alerts
4. **Given** an authenticated session, **When** the vehicles page loads, **Then** seeded vehicles appear in a table with plate, type, and status columns
5. **Given** an authenticated session, **When** the persons page loads, **Then** seeded persons appear with name, department, and access level
6. **Given** an authenticated session, **When** the search page loads and a query is entered, **Then** matching images from the seed data are displayed with similarity scores
7. **Given** an authenticated session, **When** the settings page loads, **Then** camera and zone management forms are visible and functional
8. **Given** an authenticated session, **When** the health endpoint is polled, **Then** the system status indicator shows a healthy state

---

### User Story 4 - AI Engine Performance Validation (Priority: P2)

As a technical lead, I want benchmark data for all AI capabilities (CLIP embedding, YOLO detection, face recognition, vector search) so that I can confirm the GPU acceleration is working and performance meets production requirements.

Tests must measure latency for each AI operation, verify embedding dimensions, confirm vector storage and retrieval, and validate end-to-end text-to-image search accuracy. Results should be presented in a clear performance summary.

**Why this priority**: The AI engine is the core differentiator — without verified GPU performance, the system's value proposition is unproven.

**Independent Test**: Can be run as a standalone benchmark that produces timing statistics for each AI operation.

**Acceptance Scenarios**:

1. **Given** a test image, **When** a CLIP embedding is requested, **Then** a 512-dimensional vector is returned within 200ms on average
2. **Given** a test image, **When** YOLO detection is requested, **Then** object detections are returned (or empty list for images with no recognizable objects) within 500ms
3. **Given** seeded CLIP embeddings, **When** a text query is embedded and compared against stored vectors, **Then** the top results have similarity scores that reflect semantic relevance
4. **Given** a text query, **When** the full search pipeline runs (text embed → vector search → result ranking), **Then** results are returned within 100ms total
5. **Given** multiple text queries covering different semantic categories (vehicles, persons, locations, objects), **When** each is searched, **Then** the returned results are ranked in a logically correct order

---

### User Story 5 - Gate Security Workflow Verification (Priority: P3)

As a security manager, I want to verify the complete gate access control workflow — from LPR camera detecting a vehicle, through entry decision, to exit approval — so that I can trust the automated security system.

This covers the full gate lifecycle: LPR event → vehicle lookup → permit check → entry decision → exit request → manager approval → gate override.

**Why this priority**: Gate control is a critical safety feature but depends on the backend (P1) and seed data (P1) being correct first.

**Independent Test**: Can be tested by simulating a sequence of LPR events and verifying the correct gate actions and audit trail.

**Acceptance Scenarios**:

1. **Given** a whitelisted vehicle with a valid permit, **When** an LPR entry event is detected, **Then** the vehicle is allowed entry and the event is logged
2. **Given** a vehicle without a valid permit, **When** an LPR entry event is detected, **Then** entry is denied and an alert is generated
3. **Given** a vehicle that has entered, **When** an exit event occurs and a manager approves, **Then** the exit is recorded and the gate opens
4. **Given** a gate in automatic mode, **When** a manual override is requested by an authorized user, **Then** the gate state changes and the override is logged
5. **Given** multiple gate events in sequence, **When** the gate history is queried, **Then** the complete event timeline is returned in chronological order

---

### Edge Cases

- What happens when the seed script is run twice on the same database? (Should be idempotent — no duplicate records)
- What happens when the AI engine is temporarily unreachable during embedding? (System should log failure, not crash)
- What happens when MinIO storage is full? (Upload should fail gracefully with an error message)
- What happens when a user searches with an empty query? (Should return recent images or show a helpful prompt)
- What happens when concurrent LPR events arrive for the same vehicle? (Should be processed sequentially without data corruption)
- What happens when the WebSocket connection drops? (Dashboard should reconnect automatically and resume live event display)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST populate at least 10 cameras across all three types (LPR, CCTV, PTZ) distributed across factory zones
- **FR-002**: System MUST populate at least 4 vehicles with varying plate numbers, types, and whitelisting statuses
- **FR-003**: System MUST populate at least 3 persons across different departments with different access levels
- **FR-004**: System MUST generate and store at least 10 test images in MinIO object storage with valid image URLs accessible from the dashboard
- **FR-005**: System MUST generate and store CLIP embeddings (512-dimensional vectors) for every seeded image in the vector database
- **FR-006**: System MUST support text-to-image search that returns ranked results with similarity scores
- **FR-007**: Backend test suite MUST verify all CRUD operations for vehicles, persons, cameras, and zones
- **FR-008**: Backend test suite MUST verify the complete gate LPR event workflow (entry decision, exit approval, manual override)
- **FR-009**: Backend test suite MUST verify alert lifecycle (creation, retrieval, resolution)
- **FR-010**: Backend test suite MUST verify authentication and authorization guards on all protected endpoints
- **FR-011**: Frontend test suite MUST verify every dashboard page loads successfully (HTTP 200) and contains expected content
- **FR-012**: Frontend test suite MUST verify unauthenticated access redirects to login
- **FR-013**: Frontend test suite MUST verify the login flow produces a valid session cookie
- **FR-014**: AI benchmark MUST measure and report latency for CLIP embedding, YOLO detection, face embedding, and vector search operations
- **FR-015**: Seed script MUST be idempotent — running it multiple times must not create duplicate records
- **FR-016**: Seed script MUST clean up old seed data before re-seeding to prevent accumulation
- **FR-017**: Test suite MUST produce a clear pass/fail summary report with timing statistics
- **FR-018**: Dashboard MUST display seeded camera, vehicle, and person data in tables and summary tiles
- **FR-019**: Dashboard health indicator MUST poll the API health endpoint and display connection status
- **FR-020**: Dashboard MUST reconnect to WebSocket live events automatically after connection drops

### Key Entities

- **Camera**: A surveillance device with a type (LPR, CCTV, PTZ), IP address, zone assignment, and active status
- **Vehicle**: A registered vehicle identified by plate number, with type (car/truck), department, whitelisting status, and permit requirements
- **Person**: An authorized individual with employee ID, name, department, access level, and active status
- **Image**: A captured surveillance frame stored in object storage, linked to a camera and timestamp, with metadata
- **Image Embedding**: A CLIP vector (512 dimensions) representing the visual content of an image, used for similarity search
- **Face Embedding**: A face recognition vector linked to a person, used for identity verification
- **Zone**: A defined area of the factory (gate, loading dock, warehouse, restricted zone) with associated cameras
- **Gate Event**: An LPR-triggered access control event with entry/exit decision, vehicle reference, and approval workflow
- **Alert**: A security notification with severity, status (active/resolved), and optional resolution notes
- **Permit**: A time-bound access authorization for a vehicle to enter specific zones

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 10 seeded cameras are visible in the dashboard with correct type, IP, and zone assignments
- **SC-002**: All 4 seeded vehicles appear in the vehicles page with correct plate, type, and status
- **SC-003**: All 3 seeded persons appear in the persons page with correct name, department, and access level
- **SC-004**: Text-to-image search returns relevant results for at least 8 out of 10 test queries (queries covering trucks, persons, plates, warehouse scenes, parking)
- **SC-005**: Backend API test suite achieves 100% pass rate across all endpoint tests (authentication, CRUD, gate flow, alerts, search)
- **SC-006**: Frontend page test suite achieves 100% pass rate — every page loads and contains expected content
- **SC-007**: CLIP embedding latency averages under 50ms per image (after warm-up)
- **SC-008**: Text-to-image search end-to-end latency (text embed + vector search) averages under 30ms
- **SC-009**: YOLO detection latency averages under 50ms per image (after warm-up)
- **SC-010**: Dashboard health indicator shows green (healthy) status within 5 seconds of page load
- **SC-011**: The complete test suite (backend + frontend + AI) runs in under 30 seconds
- **SC-012**: Seed script completes all phases (cameras, vehicles, persons, images, embeddings) in under 10 seconds

## Assumptions

- The application is already deployed and running on the target server with all services operational (API, dashboard, AI engine, database, MinIO, Redis, MQTT)
- The GPU server has nvidia-container-toolkit installed and AI models (CLIP, YOLO, face recognition) are loaded in the AI engine container
- The seed script runs from inside the API container where it has direct access to the database, MinIO, and AI engine via Docker networking
- Test images are programmatically generated (synthetic Pillow images) rather than sourced from real CCTV footage
- The AI engine's CLIP model produces 512-dimensional embeddings
- The search threshold for "relevant results" is a similarity score above 0.15 (based on pgvector cosine distance)
- All test scenarios use the default admin credentials (admin/acuseek)
- MinIO public base URL is configured correctly for the deployment environment (internal Docker vs. external public IP)
- The seed script is idempotent and can be re-run safely without manual database cleanup
- Performance benchmarks are measured on the Nebius GPU server and results may differ on other hardware
