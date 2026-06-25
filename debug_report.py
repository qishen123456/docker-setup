
import json

with open('config/smartask_report_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    history = data.get('history_by_scope', {}).get('user:anonymous', [])
    if history:
        print('Total records:', len(history))
        for h in history:
            if '线下业务开单金额排名前3的分公司' in h['question']:
                print()
                print('=== Found target question ===')
                print('Question:', h['question'])
                print('Updated At:', h['updatedAt'])
                result = h['reportSnapshot']['result']
                dataset_result = result['dataset_results'][0]
                report_config = dataset_result['report_config']
                query_intent = report_config.get('queryIntent') or dataset_result.get('query_intent')
                if query_intent:
                    print('Target Level:', query_intent.get('target_level'))
                agent3 = dataset_result['agent3_review']
                sql = agent3['final_sql']
                print('SQL (length:', len(sql), ')')

                import re
                matches = re.findall(r'层级\s*=\s*[\'"]([^\'"]*)[\'"]', sql)
                if matches:
                    print('Found WHERE clause 层级 = matches:', matches)
                print()
                print('=== Rows ===')
                rows = dataset_result['rows']
                for row in rows[:20]:
                    print(row['层级'], '-', row['节点名称'])
                print()
                print('=== Full SQL snippet (WITH clauses) ===')
                print(sql[:1500])
                break
