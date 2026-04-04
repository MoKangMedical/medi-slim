"""
MediSlim 永久记忆系统 — 向量数据库
ChromaDB本地存储，零成本嵌入，所有行为行动自动保存
"""

import chromadb
from chromadb.config import Settings
import json
import uuid
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path("./data/vector_memory")
DB_PATH.mkdir(parents=True, exist_ok=True)

# 初始化ChromaDB客户端（本地持久化）
client = chromadb.PersistentClient(path=str(DB_PATH))

# 创建四个记忆集合
COLLECTIONS = {
    "conversations":  client.get_or_create_collection(
        name="conversations",
        metadata={"hnsw:space": "cosine"}
    ),
    "actions":        client.get_or_create_collection(
        name="actions",
        metadata={"hnsw:space": "cosine"}
    ),
    "decisions":      client.get_or_create_collection(
        name="decisions",
        metadata={"hnsw:space": "cosine"}
    ),
    "knowledge":      client.get_or_create_collection(
        name="knowledge",
        metadata={"hnsw:space": "cosine"}
    ),
}

def _ts():
    return datetime.now().isoformat()

def _nid():
    return str(uuid.uuid4())

# ========== 核心API ==========

def remember_conversation(role, content, context="", tags=""):
    """保存对话记录"""
    cid = _nid()
    COLLECTIONS["conversations"].add(
        ids=[cid],
        documents=[content],
        metadatas=[{
            "role": role,
            "context": context,
            "tags": tags,
            "timestamp": _ts(),
            "type": "conversation"
        }]
    )
    return cid

def remember_action(action_type, description, result="", related_to=""):
    """保存行为/操作记录"""
    aid = _nid()
    COLLECTIONS["actions"].add(
        ids=[aid],
        documents=[description],
        metadatas=[{
            "action_type": action_type,
            "result": result,
            "related_to": related_to,
            "timestamp": _ts(),
            "type": "action"
        }]
    )
    return aid

def remember_decision(topic, decision, reasoning="", outcome=""):
    """保存决策记录"""
    did = _nid()
    COLLECTIONS["decisions"].add(
        ids=[did],
        documents=[decision],
        metadatas=[{
            "topic": topic,
            "reasoning": reasoning,
            "outcome": outcome,
            "timestamp": _ts(),
            "type": "decision"
        }]
    )
    return did

def remember_knowledge(domain, content, source="", importance="normal"):
    """保存知识/洞察"""
    kid = _nid()
    COLLECTIONS["knowledge"].add(
        ids=[kid],
        documents=[content],
        metadatas=[{
            "domain": domain,
            "source": source,
            "importance": importance,
            "timestamp": _ts(),
            "type": "knowledge"
        }]
    )
    return kid

# ========== 检索API ==========

def recall(query, collection="conversations", n_results=5):
    """语义搜索记忆"""
    if collection == "all":
        results = {}
        for name, col in COLLECTIONS.items():
            try:
                r = col.query(query_texts=[query], n_results=n_results)
                results[name] = {
                    "documents": r["documents"][0] if r["documents"] else [],
                    "metadatas": r["metadatas"][0] if r["metadatas"] else [],
                    "distances": r["distances"][0] if r["distances"] else []
                }
            except Exception:
                results[name] = {"documents": [], "metadatas": [], "distances": []}
        return results
    
    col = COLLECTIONS.get(collection)
    if not col:
        return {"error": f"collection '{collection}' not found"}
    
    try:
        r = col.query(query_texts=[query], n_results=n_results)
        return {
            "documents": r["documents"][0] if r["documents"] else [],
            "metadatas": r["metadatas"][0] if r["metadatas"] else [],
            "distances": r["distances"][0] if r["distances"] else []
        }
    except Exception as e:
        return {"error": str(e)}

def recall_by_time(collection="conversations", hours=24):
    """按时间检索最近记忆"""
    col = COLLECTIONS.get(collection)
    if not col:
        return {"error": f"collection '{collection}' not found"}
    
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    try:
        r = col.get(where={"timestamp": {"$gte": cutoff}}, limit=100)
        return {
            "ids": r.get("ids", []),
            "documents": r.get("documents", []),
            "metadatas": r.get("metadatas", [])
        }
    except Exception as e:
        return {"error": str(e)}

def count_all():
    """统计所有记忆数量"""
    return {name: col.count() for name, col in COLLECTIONS.items()}

# ========== 批量导入现有数据 ==========

def import_file(filepath, collection="knowledge", domain="general"):
    """从文件批量导入"""
    path = Path(filepath)
    if not path.exists():
        return f"文件不存在: {filepath}"
    
    content = path.read_text()
    # 按段落分割
    chunks = [p.strip() for p in content.split("\n\n") if p.strip()]
    
    ids = []; docs = []; metas = []
    for chunk in chunks:
        ids.append(_nid())
        docs.append(chunk[:2000])  # 限制长度
        metas.append({
            "domain": domain,
            "source": str(filepath),
            "timestamp": _ts(),
            "type": "imported"
        })
    
    col = COLLECTIONS[collection]
    if ids:
        col.add(ids=ids, documents=docs, metadatas=metas)
    
    return f"导入 {len(ids)} 条记忆到 {collection}"

# ========== HTTP服务 ==========

def run_server(port=8095):
    """运行记忆检索HTTP服务"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class MemHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            p = self.path.split("?")[0]
            if p == "/api/memory/stats":
                self._json({"collections": count_all(), "path": str(DB_PATH)})
            elif p == "/api/memory/search":
                q = self.path.split("q=")[1] if "q=" in self.path else ""
                c = self.path.split("c=")[1].split("&")[0] if "c=" in self.path else "all"
                if q:
                    result = recall(q, collection=c)
                    self._json(result)
                else:
                    self._json({"error": "missing ?q="}, 400)
            elif p == "/api/memory/recent":
                self._json(recall_by_time())
            else:
                self._json({"status": "ok", "collections": count_all()})
        
        def do_POST(self):
            l = int(self.headers.get("Content-Length", 0))
            b = json.loads(self.rfile.read(l).decode()) if l else {}
            p = self.path
            
            if p == "/api/memory/conversation":
                cid = remember_conversation(
                    b.get("role", "user"),
                    b.get("content", ""),
                    b.get("context", ""),
                    b.get("tags", "")
                )
                self._json({"saved": True, "id": cid})
            elif p == "/api/memory/action":
                aid = remember_action(
                    b.get("action_type", "general"),
                    b.get("description", ""),
                    b.get("result", ""),
                    b.get("related_to", "")
                )
                self._json({"saved": True, "id": aid})
            elif p == "/api/memory/decision":
                did = remember_decision(
                    b.get("topic", ""),
                    b.get("decision", ""),
                    b.get("reasoning", ""),
                    b.get("outcome", "")
                )
                self._json({"saved": True, "id": did})
            elif p == "/api/memory/knowledge":
                kid = remember_knowledge(
                    b.get("domain", "general"),
                    b.get("content", ""),
                    b.get("source", ""),
                    b.get("importance", "normal")
                )
                self._json({"saved": True, "id": kid})
            elif p == "/api/memory/import":
                r = import_file(b.get("filepath", ""), b.get("collection", "knowledge"))
                self._json({"result": r})
            else:
                self._json({"error": "not found"}, 404)
        
        def _json(self, d, s=200):
            self.send_response(s)
            self.send_header("Content-Type", "application/json;charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(d, ensure_ascii=False).encode())
        
        def log_message(self, *a):
            pass
    
    print(f"🧠 向量记忆系统 :{port} 已启动")
    print(f"   数据库路径: {DB_PATH}")
    print(f"   记忆总数: {count_all()}")
    HTTPServer(("0.0.0.0", port), MemHandler).serve_forever()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8095
    
    # 导入现有memory数据
    memory_dir = Path("/root/.openclaw/workspace/memory")
    if memory_dir.exists():
        for f in sorted(memory_dir.glob("*.md")):
            result = import_file(str(f), "knowledge", "project_memory")
            print(f"  {result}")
    
    print(f"\n记忆总数: {count_all()}")
    run_server(port)
