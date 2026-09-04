-- ACUSEEK PostgreSQL init
-- Enables pgvector + uuid extensions and creates base tables.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. ZONES & RESTRICTIONS
CREATE TABLE IF NOT EXISTS zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    zone_type VARCHAR(50) NOT NULL, -- 'gate', 'production', 'warehouse', 'loading_dock', 'restricted', 'perimeter'
    is_restricted BOOLEAN DEFAULT FALSE,
    min_lux_required INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. CAMERAS
CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id UUID REFERENCES zones(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    camera_type VARCHAR(50) NOT NULL, -- 'lpr', 'face', 'overview_ptz', 'fixed_dome', 'fixed_bullet'
    rtsp_url TEXT NOT NULL,
    isapi_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. VEHICLES & WHITELIST
CREATE TABLE IF NOT EXISTS vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plate_number VARCHAR(30) UNIQUE NOT NULL,
    owner_name VARCHAR(150),
    owner_phone VARCHAR(30),
    vehicle_type VARCHAR(50), -- 'truck', 'sedan', 'van', 'forklift'
    color VARCHAR(30),
    department VARCHAR(100),
    is_whitelisted BOOLEAN DEFAULT FALSE,
    requires_exit_permission BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS whitelist_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE CASCADE,
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    authorized_by VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);

-- 4. PERSONS & FACE EMBEDDINGS
CREATE TABLE IF NOT EXISTS persons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id VARCHAR(50) UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    department VARCHAR(100),
    access_level VARCHAR(50) DEFAULT 'standard', -- 'standard', 'restricted_access', 'security', 'manager'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS face_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID REFERENCES persons(id) ON DELETE CASCADE,
    embedding VECTOR(512) NOT NULL, -- InsightFace buffalo_l vector
    sample_image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. EVENT LOGGING
CREATE TABLE IF NOT EXISTS vehicle_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    camera_id UUID REFERENCES cameras(id) ON DELETE SET NULL,
    plate_number VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'entry_granted', 'entry_denied', 'exit_pending', 'exit_granted', 'exit_denied'
    direction VARCHAR(10) NOT NULL, -- 'in', 'out'
    snapshot_url TEXT,
    confidence FLOAT,
    approved_by VARCHAR(100),
    event_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS person_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID REFERENCES persons(id) ON DELETE SET NULL,
    camera_id UUID REFERENCES cameras(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL, -- 'verified', 'unauthorized_intrusion', 'unknown_visitor'
    face_snapshot_url TEXT,
    confidence FLOAT,
    event_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. ACUSEEK NATURAL LANGUAGE SEARCH INDEX
CREATE TABLE IF NOT EXISTS image_store (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id UUID REFERENCES cameras(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS image_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID REFERENCES image_store(id) ON DELETE CASCADE,
    clip_embedding VECTOR(512) NOT NULL, -- OpenCLIP ViT-B/32
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. SECURITY ALERTS
CREATE TABLE IF NOT EXISTS alert_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id UUID REFERENCES zones(id),
    camera_id UUID REFERENCES cameras(id),
    alert_type VARCHAR(50) NOT NULL, -- 'restricted_intrusion', 'unknown_vehicle', 'exit_denied', 'gate_forced'
    severity VARCHAR(20) DEFAULT 'high',
    description TEXT NOT NULL,
    snapshot_url TEXT,
    status VARCHAR(30) DEFAULT 'new', -- 'new', 'acknowledged', 'resolved', 'dismissed'
    resolved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- HNSW Vector Indexes
CREATE INDEX IF NOT EXISTS idx_face_embedding_hnsw ON face_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_clip_embedding_hnsw ON image_embeddings USING hnsw (clip_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_vehicle_events_plate ON vehicle_events(plate_number, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_alert_status ON alert_events(status, severity);
CREATE INDEX IF NOT EXISTS idx_image_store_camera_time ON image_store(camera_id, captured_at DESC);
