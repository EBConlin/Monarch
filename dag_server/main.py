from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
import uuid
import sqlite3
import json
import os

app = FastAPI()

EXPORT_DIR = "dags"
os.makedirs(EXPORT_DIR, exist_ok=True)

class DAGNode(BaseModel):
    id: str
    type: str
    content: str
    formal_spec: str = ""
    metadata: Dict[str, Any] = {}

class DAGEdge(BaseModel):
    from_: str
    to: str
    relation: str = "depends_on"

class DAGMetadata(BaseModel):
    created_by: str = "monarch-gpt"
    created_at: str = datetime.utcnow().isoformat()
    tags: List[str] = []
    description: str = ""

class DAGObject(BaseModel):
    name: str
    nodes: List[DAGNode]
    edges: List[DAGEdge]
    metadata: DAGMetadata = DAGMetadata()

@app.on_event("startup")
def startup():
    conn = sqlite3.connect("dag_memory.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS dags (
        dag_id TEXT PRIMARY KEY,
        name TEXT,
        metadata TEXT,
        nodes TEXT,
        edges TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

@app.get("/")
def read_root():
    return {"message": "Monarch DAG Server is alive"}

@app.post("/save_dag")
async def save_dag(dag: DAGObject):
    dag_id = str(uuid.uuid4())

    # Save to SQLite
    conn = sqlite3.connect("dag_memory.db")
    c = conn.cursor()
    c.execute("""
    INSERT INTO dags (dag_id, name, metadata, nodes, edges, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        dag_id,
        dag.name,
        dag.metadata.json(),
        json.dumps([n.dict() for n in dag.nodes]),
        json.dumps([{"from": e.from_, "to": e.to, "relation": e.relation} for e in dag.edges]),
        dag.metadata.created_at
    ))
    conn.commit()
    conn.close()

    # Save to JSON file
    export_path = os.path.join(EXPORT_DIR, f"{dag_id}.json")
    with open(export_path, "w") as f:
        json.dump({
            "dag_id": dag_id,
            "name": dag.name,
            "nodes": [n.dict() for n in dag.nodes],
            "edges": [{"from": e.from_, "to": e.to, "relation": e.relation} for e in dag.edges],
            "metadata": dag.metadata.dict(),
            "created_at": dag.metadata.created_at
        }, f, indent=2)

    return {"dag_id": dag_id, "message": "DAG saved successfully"}
