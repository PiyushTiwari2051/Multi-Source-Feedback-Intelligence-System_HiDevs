import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Neo4j Driver Initialization
_neo4j_driver = None
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")

if neo4j_uri and neo4j_uri.strip() and neo4j_user and neo4j_user.strip() and neo4j_password:
    try:
        from neo4j import GraphDatabase
        _neo4j_driver = GraphDatabase.driver(
            neo4j_uri.strip(), 
            auth=(neo4j_user.strip(), neo4j_password.strip())
        )
        # Verify the credentials and connection immediately
        _neo4j_driver.verify_connectivity()
        logger.info("Neo4j Graph Database connected successfully. Operating in Graph Database mode.")
    except Exception as e:
        logger.error(f"Failed to connect Neo4j client: {e}. Falling back to SQLite.")
        _neo4j_driver = None
else:
    logger.info("Neo4j credentials not configured. Operating in Local SQLite mode.")

# --- Local SQLite Helpers ---

def get_db_path() -> str:
    """
    Retrieves the SQLite database file path.
    """
    db_path = os.getenv("DB_PATH", "./data/feedback.db")
    abs_path = os.path.abspath(db_path)
    dir_name = os.path.dirname(abs_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    return abs_path

def get_connection() -> sqlite3.Connection:
    """
    Returns a new SQLite connection.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# --- Unified DB Interface ---

def init_db() -> None:
    """
    Initializes the database schema.
    For Neo4j, establishes constraint rules to keep nodes unique and lookups fast.
    For local SQLite, builds the relational table.
    """
    if _neo4j_driver is not None:
        logger.info("Verifying Neo4j graph database indexes and constraints...")
        try:
            with _neo4j_driver.session() as session:
                # Create constraints to enforce unique IDs on Review, Category, and Source nodes
                session.run("CREATE CONSTRAINT review_id IF NOT EXISTS FOR (r:Review) REQUIRE r.id IS UNIQUE")
                session.run("CREATE CONSTRAINT source_name IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE")
                session.run("CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE")
            logger.info("Neo4j Graph indexes and constraints verified.")
        except Exception as e:
            logger.warning(f"Could not establish Neo4j graph constraints: {e}")
        return

    # SQLite Fallback
    logger.info("Initializing SQLite database.")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                text TEXT NOT NULL,
                rating INTEGER,
                review_date TEXT,
                sentiment_label TEXT,
                sentiment_score REAL,
                category TEXT,
                priority_score REAL,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("Local SQLite database table verified/created.")
    except Exception as e:
        logger.critical(f"Failed to initialize SQLite database: {e}", exc_info=True)
    finally:
        conn.close()

def insert_reviews(reviews_list: List[Dict[str, Any]]) -> int:
    """
    Inserts a list of reviews. Toggles between Neo4j Cypher merges and SQLite SQL inserts.
    """
    if not reviews_list:
        return 0

    if _neo4j_driver is not None:
        # Graph Database Ingestion
        logger.info(f"Upserting {len(reviews_list)} reviews to Neo4j Graph database.")
        batch = []
        for r in reviews_list:
            batch.append({
                'id': r['id'],
                'source': r['source'],
                'text': r['text'],
                'rating': r['rating'],
                'date': r['date'],
                'sentiment_label': r['sentiment_label'],
                'sentiment_score': r['sentiment_score'],
                'category': r['category'],
                'priority_score': r.get('priority_score', 0.0)
            })

        cypher = """
        UNWIND $batch AS row
        MERGE (s:Source {name: row.source})
        MERGE (c:Category {name: row.category})
        MERGE (r:Review {id: row.id})
        SET r.text = row.text,
            r.rating = row.rating,
            r.date = row.date,
            r.sentiment_label = row.sentiment_label,
            r.sentiment_score = row.sentiment_score,
            r.priority_score = row.priority_score
        MERGE (r)-[:FROM_SOURCE]->(s)
        MERGE (r)-[:HAS_CATEGORY]->(c)
        """
        try:
            with _neo4j_driver.session() as session:
                session.run(cypher, batch=batch)
            return len(reviews_list)
        except Exception as e:
            logger.error(f"Neo4j batch upsert failed: {e}", exc_info=True)
            return 0
    else:
        # Local SQLite Ingestion
        conn = get_connection()
        inserted_count = 0
        try:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO reviews (
                    id, source, text, rating, review_date, 
                    sentiment_label, sentiment_score, category, priority_score
                ) VALUES (
                    :id, :source, :text, :rating, :date, 
                    :sentiment_label, :sentiment_score, :category, :priority_score
                )
            """, reviews_list)
            conn.commit()
            inserted_count = cursor.rowcount
            logger.info(f"Inserted or updated {inserted_count} reviews in local SQLite DB.")
        except Exception as e:
            logger.error(f"SQLite insertion failed: {e}", exc_info=True)
        finally:
            conn.close()
        return inserted_count

def get_filtered_reviews(
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetches filtered reviews from the active database.
    """
    if _neo4j_driver is not None:
        # Graph Database Query
        logger.info("Querying reviews from Neo4j.")
        
        cypher = """
        MATCH (r:Review)-[:FROM_SOURCE]->(s:Source)
        MATCH (r)-[:HAS_CATEGORY]->(c:Category)
        WHERE 1=1
        """
        params = {}
        
        if source and source != "All":
            cypher += " AND s.name = $source"
            params['source'] = source
            
        if sentiment and sentiment != "All":
            cypher += " AND r.sentiment_label = $sentiment"
            params['sentiment'] = sentiment
            
        if start_date:
            cypher += " AND r.date >= $start_date"
            params['start_date'] = start_date
            
        if end_date:
            cypher += " AND r.date <= $end_date"
            params['end_date'] = end_date
            
        cypher += """
        RETURN r.id AS id, s.name AS source, r.text AS text, r.rating AS rating, r.date AS date, 
               r.sentiment_label AS sentiment_label, r.sentiment_score AS sentiment_score, 
               c.name AS category, r.priority_score AS priority_score
        ORDER BY r.date DESC
        """
        try:
            with _neo4j_driver.session() as session:
                result = session.run(cypher, **params)
                results = []
                for record in result:
                    results.append({
                        'id': record['id'],
                        'source': record['source'],
                        'text': record['text'],
                        'rating': record['rating'],
                        'date': record['date'],
                        'sentiment_label': record['sentiment_label'],
                        'sentiment_score': record['sentiment_score'],
                        'category': record['category'],
                        'priority_score': record.get('priority_score', 0.0),
                        'ingested_at': None
                    })
                return results
        except Exception as e:
            logger.error(f"Neo4j query failed: {e}", exc_info=True)
            return []
    else:
        # Local SQLite Query
        conn = get_connection()
        query = "SELECT * FROM reviews WHERE 1=1"
        params = {}
        
        if source and source != "All":
            query += " AND source = :source"
            params['source'] = source
            
        if sentiment and sentiment != "All":
            query += " AND sentiment_label = :sentiment"
            params['sentiment'] = sentiment
            
        if start_date:
            query += " AND review_date >= :start_date"
            params['start_date'] = start_date
            
        if end_date:
            query += " AND review_date <= :end_date"
            params['end_date'] = end_date
            
        query += " ORDER BY review_date DESC"
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for r in rows:
                results.append({
                    'id': r['id'],
                    'source': r['source'],
                    'text': r['text'],
                    'rating': r['rating'],
                    'date': r['review_date'],
                    'sentiment_label': r['sentiment_label'],
                    'sentiment_score': r['sentiment_score'],
                    'category': r['category'],
                    'priority_score': r['priority_score'],
                    'ingested_at': r['ingested_at']
                })
            return results
        except Exception as e:
            logger.error(f"SQLite query failed: {e}", exc_info=True)
            return []
        finally:
            conn.close()

def update_priority_scores(scores_mapping: Dict[str, float]) -> None:
    """
    Bulk updates priority scores for each category.
    """
    if _neo4j_driver is not None:
        # Graph Database Priority Update
        logger.info("Updating priority scores in Neo4j.")
        cypher = """
        MATCH (r:Review)-[:HAS_CATEGORY]->(c:Category {name: $category})
        SET r.priority_score = $score
        """
        try:
            with _neo4j_driver.session() as session:
                for category, score in scores_mapping.items():
                    session.run(cypher, category=category, score=score)
            logger.info("Successfully updated priority scores in Neo4j.")
        except Exception as e:
            logger.error(f"Neo4j priority update failed: {e}", exc_info=True)
    else:
        # Local SQLite Priority Update
        conn = get_connection()
        try:
            cursor = conn.cursor()
            for category, score in scores_mapping.items():
                cursor.execute("""
                    UPDATE reviews 
                    SET priority_score = ? 
                    WHERE category = ?
                """, (score, category))
            conn.commit()
            logger.info("Successfully updated priority scores in SQLite database.")
        except Exception as e:
            logger.error(f"SQLite priority update failed: {e}", exc_info=True)
        finally:
            conn.close()
