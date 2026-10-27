"""Optional, parameterized Neo4j passage expansion. Graph edges are indexing
hints, never independent medical evidence. No patient data is written to Neo4j.
"""
import re

CONCEPTS = {
    "crp": ("crp", "c-reactive"), "blood_culture": ("culture",),
    "respiratory_support": ("respiratory", "cpap", "oxygen"),
    "renal_function": ("creatinine", "renal", "urine", "gentamicin"),
    "intrapartum_risk": ("gbs", "maternal", "rupture", "intrapartum"),
    "antibiotics": ("antibiotic", "penicillin", "ampicillin", "gentamicin"),
    "serial_assessment": ("trend", "serial", "reassess", "monitor"),
}


def concepts(text):
    text = text.lower()
    found=[c for c, terms in CONCEPTS.items() if any(re.search(r"\b" + re.escape(t), text) for t in terms)]
    if ('crp' in text or 'c-reactive' in text) and re.search(r'\balone\b',text):found.append('single_marker_decision')
    if 'antibiotic' in text and re.search(r'\b(stop|stopping|discontinu|withhold)',text):found.append('antibiotic_stopping_conditions')
    if re.search(r'\b(baseline|first dose|before giving)\b',text):found.append('initial_investigations')
    if re.search(r'\b(red.flag|apnoea|apnea|seizures|shock)\b',text):found.append('clinical_danger_indicators')
    if re.search(r'\b(immediate clinical assessment|review.*maternal.*history)\b',text):found.append('initial_clinical_assessment')
    return found


def query_concepts(query):
    found=concepts(query)
    specific=[c for c in found if c not in {'antibiotics','blood_culture','serial_assessment'}]
    return specific or found


def graph_candidate_ids(query, settings, limit=30):
    if not settings.enable_knowledge_graph:
        return [], "disabled"
    from neo4j import GraphDatabase
    try:
        with GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password), connection_timeout=3, max_connection_pool_size=4) as driver:
            from neo4j import Query
            rows, _, _ = driver.execute_query(Query(
                "MATCH (p:EvidencePassage)-[:MENTIONS]->(c:ClinicalConcept) "
                "WHERE c.name IN $concepts RETURN p.chunk_id AS chunk_id, count(c) AS matches "
                "ORDER BY matches DESC, chunk_id LIMIT $limit", timeout=3),
                concepts=query_concepts(query), limit=limit, database_=settings.neo4j_database, routing_="r")
        return [r["chunk_id"] for r in rows], "available"
    except Exception:
        return [], "unavailable"


def sync_passages(chunks, settings):
    from neo4j import GraphDatabase
    rows = [{"id": str(c["id"]), "concepts": concepts(c["chunk_text"])} for c in chunks]
    with GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password)) as driver:
        driver.execute_query("CREATE CONSTRAINT eos_passage_id IF NOT EXISTS FOR (p:EvidencePassage) REQUIRE p.chunk_id IS UNIQUE", database_=settings.neo4j_database)
        driver.execute_query("CREATE CONSTRAINT eos_concept_name IF NOT EXISTS FOR (c:ClinicalConcept) REQUIRE c.name IS UNIQUE", database_=settings.neo4j_database)
        for offset in range(0, len(rows), 100):
            driver.execute_query("UNWIND $rows AS row MERGE (p:EvidencePassage {chunk_id: row.id}) WITH p, row "
                                 "UNWIND row.concepts AS name MERGE (c:ClinicalConcept {name: name}) MERGE (p)-[:MENTIONS]->(c)",
                                 rows=rows[offset:offset + 100], database_=settings.neo4j_database)
    return len(rows)
