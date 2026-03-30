import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from openai import OpenAI

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from agent_registry import get_agent
from bookshelf_repository import BookshelfConfigurationError, BookshelfRepository
from config_manager import get_default_ai_model
from datasource_router import router as datasource_router


def _extract_json_block(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


class FourAgentAskService:
    def __init__(self):
        self.repository = BookshelfRepository()
        self._llm_client: Optional[OpenAI] = None
        self._llm_model: Optional[str] = None
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self._pending_ttl_seconds = 30 * 60
        self._load_llm()

    def _load_llm(self):
        config = get_default_ai_model()
        if not config:
            self._llm_client = None
            self._llm_model = None
            return
        self._llm_model = config.get("model")
        self._llm_client = OpenAI(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://api.openai.com/v1"),
        )

    def _chat(self, system_prompt: str, user_prompt: str, max_tokens: int = 2400) -> str:
        self._load_llm()
        if not self._llm_client or not self._llm_model:
            raise RuntimeError("Default AI model is not configured.")

        response = self._llm_client.chat.completions.create(
            model=self._llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
            timeout=180,
        )
        return (response.choices[0].message.content or "").strip()

    def _chat_json(self, system_prompt: str, user_prompt: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        try:
            raw = self._chat(system_prompt, user_prompt)
            return json.loads(_extract_json_block(raw))
        except Exception:
            return fallback

    def _get_agent_prompt(self, agent_no: int, fallback: str) -> str:
        agent = get_agent(agent_no)
        prompt = (agent or {}).get("system_prompt") or fallback
        knowledge = "\n".join(f"- {item}" for item in (agent or {}).get("knowledge_base", []))
        return f"{prompt}\n\n补充知识：\n{knowledge}".strip()

    @staticmethod
    def _tokenize(text: str) -> set:
        parts = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,4}", (text or "").lower())
        return {item for item in parts if item.strip()}

    def _compute_dataset_match(self, question: str, dataset: Dict[str, Any], context: Dict[str, Any]) -> int:
        q_tokens = self._tokenize(question)
        if not q_tokens:
            return 0

        synonyms = " ".join(dataset.get("synonyms", []) or [])
        dataset_text = f"{dataset.get('dataset_name', '')} {dataset.get('business_domain', '')} {synonyms}"
        dataset_tokens = self._tokenize(dataset_text)
        synonym_overlap = len(q_tokens.intersection(dataset_tokens))
        sample_score = max([int(item.get("match_score", 0)) for item in context.get("golden_sql_samples", [])] or [0])
        score = synonym_overlap * 12 + min(sample_score, 90)
        return min(score, 100)

    def _detect_ambiguity(self, question: str, ranked_candidates: List[Tuple[Dict[str, Any], int]]) -> Optional[Dict[str, Any]]:
        if not ranked_candidates:
            return None

        candidate_ids = [item[0]["id"] for item in ranked_candidates[:3]]
        ambiguous_terms = ["分公司", "组织", "代表处", "条线", "事业部", "区域", "部门", "团队"]
        if len(ranked_candidates) >= 2:
            top1_score = ranked_candidates[0][1]
            top2_score = ranked_candidates[1][1]
            if abs(top1_score - top2_score) <= 12 and top2_score >= 60:
                return {
                    "requires_confirmation": True,
                    "confirmation_role": "boss",
                    "confirmation_question": "请老板确认本次问数优先使用哪个数据集口径？",
                    "confirmation_options": [
                        f"{ranked_candidates[0][0]['dataset_name']}（优先）",
                        f"{ranked_candidates[1][0]['dataset_name']}",
                        "跨数据集汇总（拆分子任务）",
                    ],
                    "candidate_dataset_ids": candidate_ids,
                }

        if any(term in question for term in ambiguous_terms):
            return {
                "requires_confirmation": True,
                "confirmation_role": "boss",
                "confirmation_question": "请老板确认组织统计口径：",
                "confirmation_options": [
                    "仅按分公司字段统计（推荐）",
                    "按所有名称包含分公司的组织节点统计",
                    "两种口径同时输出对比",
                ],
                "candidate_dataset_ids": candidate_ids,
            }
        return None

    def _agent1_route_with_llm(self, question: str, ranked_candidates: List[Tuple[Dict[str, Any], int]]) -> Dict[str, Any]:
        top_candidates = ranked_candidates[:5]
        candidate_blocks = []
        for dataset, score in top_candidates:
            context = self.repository.get_dataset_context(int(dataset["id"]), question, top_k_samples=3)
            candidate_blocks.append(
                {
                    "dataset_id": dataset["id"],
                    "dataset_name": dataset.get("dataset_name"),
                    "business_domain": dataset.get("business_domain"),
                    "synonyms": dataset.get("synonyms", []),
                    "score_hint": score,
                    "dataset_agent1_fragments": [
                        item["prompt_content"] for item in context.get("agent_prompts", {}).get(1, [])
                    ],
                    "sample_questions": [item.get("question", "") for item in context.get("golden_sql_samples", [])[:3]],
                }
            )

        fallback = {
            "dataset_ids": [top_candidates[0][0]["id"]] if top_candidates else [],
            "intent": "detail",
            "refined_query": question,
            "decision": "generate_sql",
            "match_score": top_candidates[0][1] if top_candidates else 0,
            "requires_confirmation": False,
            "confirmation_role": "boss",
            "confirmation_question": "",
            "confirmation_options": [],
            "candidate_dataset_ids": [item[0]["id"] for item in top_candidates[:3]],
        }

        system_prompt = self._get_agent_prompt(
            1,
            "你是 Agent1 路由中枢，负责识别数据集、判断歧义、决定是否需要老板确认。",
        )
        user_prompt = f"""
用户问题：
{question}

候选数据集：
{json.dumps(candidate_blocks, ensure_ascii=False)}

请输出 JSON：
{{
  "dataset_ids": [1],
  "intent": "summary|detail|confirm",
  "refined_query": "重写后的查询",
  "decision": "direct_execute|generate_sql|wait_boss_confirm",
  "match_score": 0,
  "requires_confirmation": false,
  "confirmation_role": "boss",
  "confirmation_question": "",
  "confirmation_options": [],
  "candidate_dataset_ids": []
}}
"""
        result = self._chat_json(system_prompt, user_prompt, fallback)
        if not isinstance(result.get("dataset_ids"), list) or not result.get("dataset_ids"):
            result["dataset_ids"] = fallback["dataset_ids"]
        result["candidate_dataset_ids"] = result.get("candidate_dataset_ids") or fallback["candidate_dataset_ids"]
        result["refined_query"] = result.get("refined_query") or question
        result["intent"] = result.get("intent") or "detail"
        result["decision"] = result.get("decision") or "generate_sql"
        result["match_score"] = int(result.get("match_score") or fallback["match_score"])
        result["requires_confirmation"] = bool(result.get("requires_confirmation", False))
        return result

    def route_with_agent1(self, question: str) -> Dict[str, Any]:
        catalog = self.repository.get_agent1_catalog()
        if not catalog:
            return {
                "dataset_ids": [],
                "intent": "detail",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
            }

        candidate_contexts: List[Tuple[Dict[str, Any], Dict[str, Any], int]] = []
        for dataset in catalog:
            context = self.repository.get_dataset_context(dataset["id"], question, top_k_samples=5)
            score = self._compute_dataset_match(question, dataset, context)
            candidate_contexts.append((dataset, context, score))

        candidate_contexts.sort(key=lambda item: item[2], reverse=True)
        ranked = [(item[0], item[2]) for item in candidate_contexts]

        llm_route = self._agent1_route_with_llm(question, ranked)
        if llm_route.get("requires_confirmation"):
            llm_route["intent"] = "confirm"
            llm_route["decision"] = "wait_boss_confirm"
            return llm_route

        ambiguity = self._detect_ambiguity(question, ranked)
        if ambiguity:
            return {
                "dataset_ids": [ranked[0][0]["id"]],
                "intent": "confirm",
                "refined_query": question,
                "requires_confirmation": True,
                "decision": "wait_boss_confirm",
                "match_score": ranked[0][1],
                **ambiguity,
            }

        best_dataset, best_context, best_score = candidate_contexts[0]
        best_sample = (best_context.get("golden_sql_samples") or [{}])[0]
        best_sample_score = int(best_sample.get("match_score", 0))
        direct_execute = best_score >= 90 and best_sample_score >= 90 and bool(best_sample.get("sql_text"))

        return {
            "dataset_ids": llm_route.get("dataset_ids") or [best_dataset["id"]],
            "intent": llm_route.get("intent") or "detail",
            "refined_query": llm_route.get("refined_query") or question,
            "requires_confirmation": False,
            "decision": "direct_execute" if direct_execute else "generate_sql",
            "match_score": best_score,
            "matched_sample_id": best_sample.get("id") if direct_execute else None,
            "matched_sample_sql": best_sample.get("sql_text") if direct_execute else "",
            "split_queries": [
                {"dataset_id": item, "sub_query": llm_route.get("refined_query") or question}
                for item in (llm_route.get("dataset_ids") or [best_dataset["id"]])
            ],
        }

    def _build_context_blob(self, context: Dict[str, Any]) -> str:
        dictionary_lines = []
        for item in context.get("data_dictionary", [])[:150]:
            dictionary_lines.append(
                f"{item['table_name']}.{item['column_name']} => semantic={item['semantic_name']}, "
                f"jsonb_key={item.get('jsonb_key')}, extraction={item.get('extraction_rule', '')}"
            )

        schema_lines = []
        for item in context.get("schema_definition", [])[:30]:
            schema_lines.append(f"TABLE={item['table_name']}\nDDL={item['ddl_sql']}")

        relation_lines = []
        for item in context.get("table_relations", [])[:30]:
            relation_lines.append(
                f"{item['left_table']}.{item['left_key']} {item['relation_type']} "
                f"{item['right_table']}.{item['right_key']}"
            )

        sample_lines = []
        for index, item in enumerate(context.get("golden_sql_samples", []), start=1):
            sample_lines.append(
                f"[Golden {index}] score={item.get('match_score', 0)} question={item.get('question')}\nSQL:\n{item.get('sql_text')}"
            )

        return "\n\n".join(
            [
                f"LLD:\n{context.get('lld_document', {}).get('content', '')}",
                "Data Dictionary:\n" + "\n".join(dictionary_lines),
                "Schema Definition:\n" + "\n\n".join(schema_lines),
                "Join Relations:\n" + "\n".join(relation_lines),
                "Golden SQL Samples:\n" + "\n\n".join(sample_lines),
            ]
        )

    def _agent2_generate_sql(self, question: str, context: Dict[str, Any], dataset_prompt: str) -> Dict[str, Any]:
        system_prompt = self._get_agent_prompt(
            2,
            "你是 Agent2 SQL 架构师，只能生成安全的只读 PostgreSQL SQL。",
        )
        user_prompt = f"""
用户问题：
{question}

数据集专属提示（Agent2）：
{dataset_prompt}

书架上下文：
{self._build_context_blob(context)}

请输出 JSON：
{{
  "sql": "最终 PostgreSQL SQL",
  "notes": "生成说明"
}}
"""
        result = self._chat_json(system_prompt, user_prompt, {"sql": "", "notes": "agent2 fallback"})
        sql_text = (result.get("sql") or "").strip()
        sql_text = re.sub(r"^```sql\s*", "", sql_text, flags=re.IGNORECASE).strip()
        sql_text = re.sub(r"\s*```$", "", sql_text).strip()
        if (not sql_text) or ("..." in sql_text):
            fallback = (context.get("golden_sql_samples") or [{}])[0]
            fallback_sql = (fallback.get("sql_text") or "").strip()
            if fallback_sql:
                sql_text = fallback_sql
                result["notes"] = "agent2 fallback to golden_sql_sample"
        result["sql"] = sql_text
        return result

    def _agent3_review(
        self,
        question: str,
        route: Dict[str, Any],
        sql_text: str,
        context: Dict[str, Any],
        dataset_prompt: str,
    ) -> Dict[str, Any]:
        system_prompt = self._get_agent_prompt(
            3,
            "你是 Agent3 SQL 审计员，负责复核 SQL 是否违反业务口径和安全规则。",
        )
        user_prompt = f"""
原始问题：
{question}

Agent1 路由结果：
{json.dumps(route, ensure_ascii=False)}

待复核 SQL：
{sql_text}

LLD：
{context.get('lld_document', {}).get('content', '')}

数据集专属提示（Agent3）：
{dataset_prompt}

请输出 JSON：
{{
  "approved": true,
  "final_sql": "复核后的最终 SQL",
  "review_summary": "复核结论",
  "risks": ["..."],
  "fixes": ["..."]
}}
"""
        fallback = {
            "approved": True,
            "final_sql": sql_text,
            "review_summary": "review fallback",
            "risks": [],
            "fixes": [],
        }
        result = self._chat_json(system_prompt, user_prompt, fallback)
        if not result.get("final_sql"):
            result["final_sql"] = sql_text
        return result

    def _execute_sql(self, source_id: int, final_sql: str) -> Dict[str, Any]:
        vn, error = datasource_router.get_vanna_for_source(source_id)
        if error:
            raise RuntimeError(error)

        dataframe = vn.run_sql(final_sql)
        if dataframe is None or dataframe.empty:
            return {"columns": [], "rows": [], "row_count": 0}

        columns = list(dataframe.columns)
        rows = []
        for _, row in dataframe.iterrows():
            item = {}
            for column in columns:
                value = row[column]
                if hasattr(value, "isoformat"):
                    value = value.isoformat()
                elif hasattr(value, "item"):
                    value = value.item()
                elif hasattr(value, "normalize"):
                    value = float(value)
                elif value != value:
                    value = None
                item[column] = value
            rows.append(item)
        return {"columns": columns, "rows": rows, "row_count": len(rows)}

    def _agent4_analysis(self, question: str, context: Dict[str, Any], review: Dict[str, Any], result: Dict[str, Any]) -> str:
        system_prompt = self._get_agent_prompt(
            4,
            "你是 Agent4 业务分析官，负责输出老板视角的经营分析结论。",
        )
        dataset_prompt = "\n\n".join(
            item["prompt_content"] for item in context.get("agent_prompts", {}).get(4, [])
        )
        user_prompt = f"""
原始问题：
{question}

LLD 背景：
{context.get('lld_document', {}).get('content', '')}

Agent3 复核结果：
{json.dumps(review, ensure_ascii=False)}

结果预览（前30行）：
{json.dumps(result.get('rows', [])[:30], ensure_ascii=False)}

数据集专属提示（Agent4）：
{dataset_prompt}
"""
        try:
            return self._chat(system_prompt, user_prompt, max_tokens=1600)
        except Exception as exc:
            return f"Agent4 analysis failed: {exc}"

    def _cleanup_expired_sessions(self):
        now = time.time()
        expired_ids = [sid for sid, item in self._pending_confirmations.items() if now - item.get("created_at", now) > self._pending_ttl_seconds]
        for sid in expired_ids:
            self._pending_confirmations.pop(sid, None)

    def _create_confirmation_session(self, question: str, route: Dict[str, Any]) -> str:
        self._cleanup_expired_sessions()
        session_id = str(uuid4())
        self._pending_confirmations[session_id] = {
            "question": question,
            "route": route,
            "created_at": time.time(),
        }
        return session_id

    def _run_pipeline(self, question: str, route: Dict[str, Any], started: float, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        dataset_ids = route.get("dataset_ids", [])
        if not dataset_ids:
            return {"error": "Agent1 did not provide dataset_ids."}

        dataset_results = []
        for dataset_id in dataset_ids:
            context = self.repository.get_dataset_context(int(dataset_id), route.get("refined_query", question))
            prompts = context.get("agent_prompts", {})
            agent2_prompt = "\n\n".join(item["prompt_content"] for item in prompts.get(2, []))
            agent3_prompt = "\n\n".join(item["prompt_content"] for item in prompts.get(3, []))

            if route.get("decision") == "direct_execute" and route.get("matched_sample_sql"):
                sql_text = route.get("matched_sample_sql")
                steps.append({"title": "Agent1 高匹配直执行", "duration": 0, "status": "success"})
            else:
                step_started = time.time()
                agent2_result = self._agent2_generate_sql(route.get("refined_query", question), context, agent2_prompt)
                sql_text = (agent2_result.get("sql") or "").strip()
                if not sql_text:
                    return {"error": f"Agent2 generated empty SQL. detail={agent2_result}"}
                steps.append(
                    {
                        "title": "Agent2 SQL 生成",
                        "duration": round((time.time() - step_started) * 1000, 2),
                        "status": "success",
                    }
                )

            step_started = time.time()
            review = self._agent3_review(question, route, sql_text, context, agent3_prompt)
            final_sql = review.get("final_sql", sql_text)
            steps.append(
                {
                    "title": "Agent3 全量复核",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

            step_started = time.time()
            try:
                result = self._execute_sql(context["dataset"]["source_id"], final_sql)
            except Exception as exec_error:
                fallback_sample = (context.get("golden_sql_samples") or [{}])[0]
                fallback_sql = (fallback_sample.get("sql_text") or "").strip()
                if fallback_sql and fallback_sql != final_sql:
                    review["fallback_reason"] = f"execute failed, fallback to golden sql: {exec_error}"
                    final_sql = fallback_sql
                    result = self._execute_sql(context["dataset"]["source_id"], final_sql)
                else:
                    raise
            steps.append(
                {
                    "title": "系统执行 SQL",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

            step_started = time.time()
            analysis_text = self._agent4_analysis(question, context, review, result)
            steps.append(
                {
                    "title": "Agent4 业务解读",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

            dataset_results.append(
                {
                    "dataset_id": context["dataset"]["id"],
                    "dataset_code": context["dataset"]["dataset_code"],
                    "dataset_name": context["dataset"]["dataset_name"],
                    "source_id": context["dataset"]["source_id"],
                    "agent3_review": review,
                    "columns": result["columns"],
                    "rows": result["rows"],
                    "row_count": result["row_count"],
                    "analysis": analysis_text,
                    "sql": final_sql,
                }
            )

        primary = dataset_results[0]
        return {
            "question": question,
            "route": route,
            "dataset_results": dataset_results,
            "data_source": primary["dataset_name"],
            "sql": primary["sql"],
            "columns": primary["columns"],
            "rows": primary["rows"],
            "row_count": primary["row_count"],
            "analysis": primary["analysis"],
            "steps": steps,
            "requires_confirmation": False,
            "total_duration": round((time.time() - started) * 1000, 2),
        }

    def ask(self, question: str, preferred_dataset_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        question = (question or "").strip()
        started = time.time()
        steps: List[Dict[str, Any]] = []
        if not question:
            return {"error": "Question cannot be empty."}
        if not self.repository.is_ready():
            try:
                self.repository.ensure_schema()
            except BookshelfConfigurationError as exc:
                return {"error": str(exc)}
            if not self.repository.is_ready():
                return {
                    "error": (
                        "Bookshelf metadata tables are not ready. "
                        "Please run backend/migrations/20260330_bookshelf_schema.sql first."
                    )
                }

        try:
            step_started = time.time()
            route = self.route_with_agent1(question)
            if preferred_dataset_ids:
                route["dataset_ids"] = [int(item) for item in preferred_dataset_ids]
                route["requires_confirmation"] = False
                route["decision"] = "generate_sql"
                route["intent"] = "detail"
                route["preferred_dataset_override"] = True
            steps.append(
                {
                    "title": "Agent1 语义路由",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

            if route.get("requires_confirmation"):
                session_id = self._create_confirmation_session(question, route)
                return {
                    "question": question,
                    "requires_confirmation": True,
                    "confirmation_role": route.get("confirmation_role", "boss"),
                    "confirmation_question": route.get("confirmation_question"),
                    "confirmation_options": route.get("confirmation_options", []),
                    "session_id": session_id,
                    "handoff_to": "boss",
                    "route": route,
                    "steps": steps,
                    "sql": "",
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "analysis": "等待老板确认后继续执行。",
                    "total_duration": round((time.time() - started) * 1000, 2),
                }

            return self._run_pipeline(question, route, started, steps)
        except (BookshelfConfigurationError, ValueError) as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Four-agent ask failed: {exc}"}

    def confirm_by_boss(self, session_id: str, selected_option: str, selected_dataset_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        started = time.time()
        steps: List[Dict[str, Any]] = []
        self._cleanup_expired_sessions()

        if not session_id:
            return {"error": "session_id is required."}

        pending = self._pending_confirmations.get(session_id)
        if not pending:
            return {"error": "Confirmation session not found or expired."}

        question = pending["question"]
        route = dict(pending["route"])

        if selected_dataset_ids:
            route["dataset_ids"] = [int(item) for item in selected_dataset_ids]
        else:
            option_text = (selected_option or "").strip()
            if not option_text:
                return {"error": "selected_option is required when selected_dataset_ids is empty."}
            candidate_ids = route.get("candidate_dataset_ids", []) or route.get("dataset_ids", [])
            if "跨数据集" in option_text and len(candidate_ids) >= 2:
                route["dataset_ids"] = candidate_ids[:2]
            else:
                route["dataset_ids"] = [candidate_ids[0]] if candidate_ids else route.get("dataset_ids", [])

        route["requires_confirmation"] = False
        route["decision"] = "generate_sql"
        route["boss_confirmation"] = {
            "selected_option": selected_option or "",
            "selected_dataset_ids": route.get("dataset_ids", []),
            "confirmed_at": int(time.time()),
        }

        steps.append(
            {
                "title": "老板确认口径",
                "duration": 0,
                "status": "success",
                "message": selected_option or "",
            }
        )

        result = self._run_pipeline(question, route, started, steps)
        result["session_id"] = session_id
        self._pending_confirmations.pop(session_id, None)
        return result


four_agent_ask_service = FourAgentAskService()
