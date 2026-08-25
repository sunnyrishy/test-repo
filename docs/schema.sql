-- Full schema for the AI Job Intelligence database, through migration 0002.
--
-- For a CLI-free setup: paste this into your provider's SQL editor (Neon,
-- Supabase, or Vercel Postgres) once, before the first deploy.
--
-- It creates alembic_version and stamps it at 0002, so later migrations run
-- normally with `alembic upgrade head` when you do have a terminal.
--
-- Regenerate with:
--   cd backend && DATABASE_URL=<url> alembic upgrade head --sql

BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE jobs (
    id SERIAL NOT NULL, 
    external_id VARCHAR(255) NOT NULL, 
    source VARCHAR(64) NOT NULL, 
    company VARCHAR(255) NOT NULL, 
    title VARCHAR(512) NOT NULL, 
    location VARCHAR(512), 
    country VARCHAR(8), 
    workplace_type VARCHAR(32), 
    employment_type VARCHAR(32), 
    description TEXT, 
    application_url TEXT, 
    source_url TEXT, 
    posted_at TIMESTAMP WITH TIME ZONE, 
    source_updated_at TIMESTAMP WITH TIME ZONE, 
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    last_verified_at TIMESTAMP WITH TIME ZONE, 
    freshness_status VARCHAR(16) DEFAULT 'UNKNOWN', 
    salary_min BIGINT, 
    salary_max BIGINT, 
    currency VARCHAR(8), 
    fingerprint VARCHAR(128), 
    canonical_job_id INTEGER, 
    filter_status VARCHAR(16) DEFAULT 'PENDING', 
    filter_rejection_reason VARCHAR(64), 
    is_active BOOLEAN DEFAULT true, 
    status VARCHAR(16) DEFAULT 'NEW', 
    status_changed_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    CONSTRAINT uq_jobs_source_external_id UNIQUE (source, external_id), 
    FOREIGN KEY(canonical_job_id) REFERENCES jobs (id) ON DELETE SET NULL
);

CREATE INDEX ix_jobs_fingerprint ON jobs (fingerprint);

CREATE INDEX ix_jobs_posted_at ON jobs (posted_at);

CREATE TABLE job_sources (
    id SERIAL NOT NULL, 
    job_id INTEGER NOT NULL, 
    source VARCHAR(64) NOT NULL, 
    source_job_id VARCHAR(255) NOT NULL, 
    source_url TEXT, 
    application_url TEXT, 
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    CONSTRAINT uq_job_sources_source_job UNIQUE (source, source_job_id), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE
);

CREATE TABLE discovery_runs (
    id SERIAL NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    finished_at TIMESTAMP WITH TIME ZONE, 
    discovered INTEGER DEFAULT '0', 
    duplicates INTEGER DEFAULT '0', 
    stored INTEGER DEFAULT '0', 
    hard_filter_failures INTEGER DEFAULT '0', 
    passed_filters INTEGER DEFAULT '0', 
    per_source TEXT, 
    errors TEXT, 
    PRIMARY KEY (id)
);

CREATE TABLE candidate_profile (
    id SERIAL NOT NULL, 
    profile_json JSONB NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id)
);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

CREATE TABLE job_verifications (
    id SERIAL NOT NULL, 
    job_id INTEGER NOT NULL, 
    decision VARCHAR(16) NOT NULL, 
    confidence FLOAT DEFAULT '0', 
    role_match BOOLEAN, 
    entry_level BOOLEAN, 
    experience_match BOOLEAN, 
    degree_match BOOLEAN, 
    graduation_match BOOLEAN, 
    location_match BOOLEAN, 
    employment_match BOOLEAN, 
    citizenship_required BOOLEAN, 
    security_clearance_required BOOLEAN, 
    experience_required INTEGER, 
    experience_type VARCHAR(24), 
    education_required TEXT, 
    work_authorization_status VARCHAR(32) DEFAULT 'UNKNOWN', 
    sponsorship_status VARCHAR(32) DEFAULT 'NOT_SPECIFIED', 
    matched_skills JSONB DEFAULT '[]', 
    missing_skills JSONB DEFAULT '[]', 
    rejection_reasons JSONB DEFAULT '[]', 
    ai_summary TEXT, 
    model VARCHAR(128), 
    content_fingerprint VARCHAR(64), 
    profile_fingerprint VARCHAR(64), 
    verified_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    UNIQUE (job_id), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE
);

CREATE INDEX ix_job_verifications_decision ON job_verifications (decision);

CREATE TABLE job_scores (
    id SERIAL NOT NULL, 
    job_id INTEGER NOT NULL, 
    role_score FLOAT DEFAULT '0', 
    experience_score FLOAT DEFAULT '0', 
    skill_score FLOAT DEFAULT '0', 
    degree_score FLOAT DEFAULT '0', 
    graduation_score FLOAT DEFAULT '0', 
    work_auth_score FLOAT DEFAULT '0', 
    location_score FLOAT DEFAULT '0', 
    salary_score FLOAT DEFAULT '0', 
    company_score FLOAT DEFAULT '0', 
    overall_score FLOAT DEFAULT '0', 
    classification VARCHAR(24) DEFAULT 'BELOW_THRESHOLD', 
    verified_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    UNIQUE (job_id), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE
);

CREATE INDEX ix_job_scores_overall_score ON job_scores (overall_score);

CREATE TABLE notifications (
    id SERIAL NOT NULL, 
    job_id INTEGER NOT NULL, 
    channel VARCHAR(32) NOT NULL, 
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE
);

CREATE INDEX ix_notifications_job_channel ON notifications (job_id, channel);

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

COMMIT;

