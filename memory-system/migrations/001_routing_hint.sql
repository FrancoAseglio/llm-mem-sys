-- 001: relation routing hints. Only for databases created before routing existed;
-- a fresh database gets this from schema.sql. Safe to run more than once.

ALTER TABLE relation_types ADD COLUMN IF NOT EXISTS routing_hint TEXT;

UPDATE relation_types
   SET routing_hint = 'Relevant to food, snacks, meals, recipes, restaurants, cooking and medicines.'
 WHERE name = 'allergic_to';

UPDATE relation_types
   SET routing_hint = 'Relevant to food, meals, recipes, cooking and what to avoid or skip.'
 WHERE name = 'dislikes';
