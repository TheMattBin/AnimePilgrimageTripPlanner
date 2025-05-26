For home assistant project using multi-agent model

```
User Interface (Home Assistant) 
       ↓
Orchestrator / Router (API Gateway)
       ↓
+----------------+    +----------------+
| Medical Agent  |    | General Q&A Agent |
+----------------+    +----------------+
       ↓                      ↓
          vLLM Inference Server (OpenAI-compatible API)
```
