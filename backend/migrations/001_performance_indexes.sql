-- Performance Optimization Migration
-- Date: 2026-01-06
-- Description: Add missing indexes and GIN indexes for JSON columns to improve query performance

-- ==================== BASIC INDEXES ====================

-- IPAddress indexes (for IPAM filtering and search)
CREATE INDEX IF NOT EXISTS ix_ip_addresses_status ON ip_addresses (status);
CREATE INDEX IF NOT EXISTS ix_ip_addresses_hostname ON ip_addresses (hostname);
CREATE INDEX IF NOT EXISTS ix_ip_addresses_subnet_id ON ip_addresses (subnet_id);
CREATE INDEX IF NOT EXISTS ix_ip_addresses_equipment_id ON ip_addresses (equipment_id);

-- ==================== GIN INDEXES FOR JSON COLUMNS ====================
-- GIN indexes significantly speed up JSON containment and key existence queries

-- User permissions (JSON array of permission strings)
-- Used for permission-based filtering: WHERE permissions @> '["ipam"]'
CREATE INDEX IF NOT EXISTS ix_users_permissions_gin ON users USING GIN (permissions jsonb_path_ops);

-- EquipmentModel specs (JSON object for hardware specifications)
-- Used for searching equipment by specs: WHERE specs @> '{"cpu": "Xeon"}'
CREATE INDEX IF NOT EXISTS ix_equipment_models_specs_gin ON equipment_models USING GIN (specs jsonb_path_ops);

-- KnowledgeArticle tags (JSON array of tag strings)
-- Used for filtering articles by tags: WHERE tags @> '["network"]'
CREATE INDEX IF NOT EXISTS ix_knowledge_articles_tags_gin ON knowledge_articles USING GIN (tags jsonb_path_ops);

-- AuditLog changes and extra_data (for audit searching)
-- Used for searching audit logs by change details
CREATE INDEX IF NOT EXISTS ix_audit_logs_changes_gin ON audit_logs USING GIN (changes jsonb_path_ops);
CREATE INDEX IF NOT EXISTS ix_audit_logs_extra_data_gin ON audit_logs USING GIN (extra_data jsonb_path_ops);

-- SLAPolicy business_days (JSON array of integers)
-- Used for SLA calculation queries
CREATE INDEX IF NOT EXISTS ix_sla_policies_business_days_gin ON sla_policies USING GIN (business_days jsonb_path_ops);

-- Webhook events (JSON array of event strings)
-- Used for filtering webhooks by subscribed events
CREATE INDEX IF NOT EXISTS ix_webhooks_events_gin ON webhooks USING GIN (events jsonb_path_ops);

-- ==================== PARTIAL INDEXES FOR COMMON FILTERS ====================

-- Active equipment only (most common query pattern)
CREATE INDEX IF NOT EXISTS ix_equipment_active ON equipment (status) WHERE status IN ('in_service', 'maintenance');

-- Unread notifications (polled frequently)
CREATE INDEX IF NOT EXISTS ix_notifications_unread ON notifications (user_id, created_at DESC) WHERE is_read = false;

-- Open tickets (dashboard and lists)
CREATE INDEX IF NOT EXISTS ix_tickets_open ON tickets (status, priority, created_at DESC) WHERE status NOT IN ('closed', 'resolved');

-- Active contracts (expiration alerts)
CREATE INDEX IF NOT EXISTS ix_contracts_active ON contracts (end_date) WHERE status = 'active';

-- ==================== COMPOSITE INDEXES FOR COMMON QUERIES ====================

-- Equipment list with status filter (most common inventory query)
CREATE INDEX IF NOT EXISTS ix_equipment_entity_status ON equipment (entity_id, status);

-- Tickets by assignee with status (technician dashboard)
CREATE INDEX IF NOT EXISTS ix_tickets_assignee_status ON tickets (assigned_to_id, status);

-- IP addresses by subnet and status (IPAM listing)
CREATE INDEX IF NOT EXISTS ix_ip_addresses_subnet_status ON ip_addresses (subnet_id, status);

-- ==================== ANALYZE TABLES ====================
-- Update statistics for query planner

ANALYZE users;
ANALYZE ip_addresses;
ANALYZE equipment;
ANALYZE equipment_models;
ANALYZE tickets;
ANALYZE notifications;
ANALYZE contracts;
ANALYZE audit_logs;
ANALYZE knowledge_articles;
ANALYZE webhooks;
ANALYZE sla_policies;
