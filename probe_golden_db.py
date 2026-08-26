import sys, os
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='postgres', port=5432, dbname='postgres', user='postgres', password='6670326')
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
SELECT id, intent_type, question, sql_text, quality_score, tags
FROM bs_golden_sql_samples
WHERE dataset_id = 3 AND is_active = TRUE
ORDER BY quality_score DESC, id ASC
LIMIT 40
""")
target_id = 2634
for s in cur.fetchall():
    if s['id'] == target_id:
        print('====== TARGET SAMPLE 2634 ======')
        print('intent:', s['intent_type'])
        print('question:', s['question'])
        print('quality_score:', s['quality_score'])
        print('tags:', s['tags'])
        print()
        print('FULL SQL:')
        print(s['sql_text'])
        print()
        print('====== END ======')
        break
    print(f"[{s['id']}] intent={s['intent_type']} q={(s['question'] or '')[:60]} qlty={s['quality_score']}")