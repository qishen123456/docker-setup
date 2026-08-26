import sys, contextlib, io, json
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)

from four_agent_ask import four_agent_ask_service as svc
from bookshelf_repository import BookshelfRepository

repo = BookshelfRepository()
ctx = repo.get_dataset_context(3, '商用事业部整体达成率是多少', top_k_samples=5)
samples = ctx.get('golden_sql_samples') or []
print('==== retrieved samples count:', len(samples), '====')
for i, s in enumerate(samples):
    print(f'rank {i}: id={s.get("id")} score={s.get("match_score")} question={s.get("question")[:60]} intent={s.get("intent_type")}')

# Also compute the score manually
print()
print('==== manually compute score for 2634 ====')
import re
def _tokenize(text):
    parts = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,4}", (text or "").lower())
    return {item for item in parts if item.strip()}

def question_key(value):
    text = re.sub(r"[\s？?。.!！,，、：:；;（）()]+", "", str(value or "").lower())
    text = re.sub(r"^(请问|帮我|帮忙|麻烦|查一下|看一下|查询|分析一下|我想知道)+", "", text)
    text = re.sub(r"(呢|啊|呀|吗|么|吧)$", "", text)
    text = text.replace("消费者事业部", "").replace("消费事业部", "").replace("消费者", "")
    text = text.replace("商用事业部", "").replace("商用", "")
    return text

q = '商用事业部整体达成率是多少'
sample_q = '商用事业部整体达成率是多少'
qk = question_key(q)
sqk = question_key(sample_q)
print(f'query_key = "{qk}"')
print(f'sample_key = "{sqk}"')
print(f'normalized_hit = {1 if sqk == qk else 0}  (would contribute *90)')
print(f'contains_hit = {1 if sqk and qk and sqk != qk and (sqk in qk or qk in sqk) else 0} (would contribute *60)')
qt = _tokenize(q)
st = _tokenize(sample_q)
print(f'overlap = {len(qt & st)}  (would contribute *12)')