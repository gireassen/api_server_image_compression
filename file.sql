CREATE TABLE files (
    id UUID PRIMARY KEY,
    original_name VARCHAR(255),
    file_path VARCHAR(255),
    status VARCHAR(20) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT NOW()
);