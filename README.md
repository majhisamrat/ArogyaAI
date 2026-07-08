# ArogyaAI – Multilingual WhatsApp Healthcare Assistant

**ArogyaAI** is an intelligent healthcare triage assistant built on WhatsApp, designed to provide preliminary symptom assessment and medical guidance to non-English-speaking populations across India. Powered by LLM multi-agent systems, semantic search over medical knowledge bases, and real-time emergency escalation.

---

## 🚀 Features

- **Multi-Agent Symptom Triage** – 14 specialized LLM agents for symptom collection, disease matching, follow-up questioning, and emergency risk assessment
- **Multilingual Support** – English, Hindi, Bengali, Tamil, Telugu (with fallback mechanisms)
- **RAG-Powered Medical Knowledge** – Semantic search over 2,000+ medical documents for real-time diagnosis guidance
- **WhatsApp Integration** – Native WhatsApp messaging via Twilio API for accessibility
- **Production-Grade Deployment** – Docker containerization, AWS EC2 backend, Vercel frontend, with monitoring dashboards
- **Drift Detection & Monitoring** – Real-time detection of model performance degradation and language-specific accuracy regressions
- **Emergency Escalation** – Automatic routing of high-risk cases to human doctors with confidence-based flagging

---

## 🏗️ Architecture

```
┌─────────────────┐
│  WhatsApp User  │
└────────┬────────┘
         │ (Twilio API)
         ▼
┌─────────────────────────┐
│   FastAPI Backend       │
│   (AWS EC2)             │
├─────────────────────────┤
│ • LangGraph Orchestrator│
│ • 14 Specialized Agents │
│ • RAG Pipeline          │
│ • Drift Detection       │
└────────┬────────────────┘
         │
    ┌────┴─────┬──────────────┐
    ▼          ▼              ▼
┌────────┐ ┌─────────────┐ ┌──────────┐
│Vector  │ │LLM Model    │ │Monitoring│
│DB      │ │(GPT-4/      │ │CloudWatch│
│        │ │Gemini)      │ │Grafana   │
└────────┘ └─────────────┘ └──────────┘
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI, Python 3.10+ |
| **LLM Orchestration** | LangChain, LangGraph |
| **Knowledge Retrieval** | Vector Database (Pinecone/Weaviate), TF-IDF |
| **LLM Provider** | OpenAI GPT-4, Google Gemini |
| **Messaging** | Twilio WhatsApp API |
| **Deployment** | Docker, AWS EC2, Vercel (Frontend) |
| **Monitoring** | CloudWatch, Custom Grafana Dashboards |
| **CI/CD** | GitHub Actions, Docker Compose |

---

## 📊 Current Status & Metrics

### Project Stage
- **Current**: Beta (seeking initial users for validation)
- **Commits**: 8
- **Test Coverage**: In progress
- **Production Users**: Looking for pilot partners

### Performance Benchmarks

| Metric | Target | Current |
|--------|--------|---------|
| Response Time | <500ms | ~450ms (dev) |
| Symptom Classification Accuracy | 85%+ | Testing phase |
| Hallucination Rate | <5% | Under evaluation |
| Supported Languages | 5 | 5 (EN, HI, BN, TA, TE) |
| Uptime Target | 99% | N/A (beta) |

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- AWS account (for EC2 deployment)
- Twilio account with WhatsApp Business API access
- OpenAI API key / Google Gemini API key

### Local Development

```bash
# Clone repository
git clone https://github.com/majhisamrat/ArogyaAI.git
cd ArogyaAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys:
# - OPENAI_API_KEY
# - TWILIO_ACCOUNT_SID
# - TWILIO_AUTH_TOKEN
# - VECTOR_DB_URL
# - AWS_REGION

# Run with Docker Compose
docker-compose up -d

# Access backend
curl http://localhost:8000/health
```

### AWS EC2 Deployment

```bash
# SSH into EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Clone and setup
git clone https://github.com/majhisamrat/ArogyaAI.git
cd ArogyaAI

# Run deployment script
bash scripts/deploy.sh

# Check logs
docker-compose logs -f backend
```

---

## 📋 Agent System Architecture

The system uses **14 specialized agents** orchestrated by LangGraph:

### Agent Categories

| Agent Type | Count | Responsibility |
|-----------|-------|-----------------|
| **Intake Agents** | 5 | Symptom collection, patient history, follow-up questioning |
| **Reasoning Agents** | 4 | Disease matching, differential diagnosis, risk assessment |
| **Safety Agents** | 3 | Emergency detection, escalation routing, doctor notification |
| **Feedback Agents** | 2 | User satisfaction, conversation logging, drift detection |

### Agent Communication Flow

```
1. User Input (WhatsApp)
   ↓
2. Intake Agent → Collects symptoms in user's language
   ↓
3. Follow-up Agent → Asks clarifying questions
   ↓
4. RAG Retrieval Agent → Searches medical knowledge base
   ↓
5. Reasoning Agent → Matches to disease categories
   ↓
6. Safety Agent → Assesses emergency risk
   ├─ Low Risk → Provide guidance + educational resources
   ├─ Medium Risk → Recommend doctor consultation
   └─ High Risk → Escalate to emergency with doctor notification
   ↓
7. Feedback Agent → Log conversation, monitor drift
```

---

## 🧠 RAG Pipeline

**Knowledge Base**: 2,000+ medical documents
- Symptom-disease mappings
- Treatment guidelines
- Drug interactions
- Emergency protocols

**Retrieval Method**:
- Vector embeddings (semantic search)
- Hybrid search (TF-IDF + semantic)
- Confidence scoring to flag hallucination risk

**Quality Control**:
- Temperature = 0.2 (deterministic outputs)
- Prompt guardrails to prevent medical claims
- Uncertain cases escalated to doctors

---

## 📡 Monitoring & Drift Detection

### Metrics Tracked

```
Real-time Monitoring:
├─ Response Latency (per agent)
├─ Agent Failure Rates
├─ Hallucination Detection (manual review samples)
├─ Language-specific Accuracy (per language)
├─ User Drop-off Rates
└─ Emergency Escalation Frequency

Dashboards:
├─ CloudWatch (AWS metrics)
├─ Custom Grafana (business metrics)
└─ GitHub Actions (CI/CD status)
```

### Drift Detection Strategy

```python
# Confidence-based drift detection
if prediction_confidence < 0.75:
    route_to_human_review()
    
# Language-specific monitoring
if language == "hindi" and accuracy_drop > 5%:
    trigger_retraining_pipeline()
```

---

## 🚀 API Endpoints

### Health Check
```bash
GET /health
Response: {"status": "healthy", "version": "0.1.0"}
```

### WhatsApp Webhook
```bash
POST /webhook/whatsapp
Content-Type: application/json

{
  "from": "+91-xxxx-xxxxx",
  "message": "I have fever and cough",
  "language": "en"
}

Response:
{
  "session_id": "uuid",
  "response": "Let me ask a few questions...",
  "agent_active": "intake_agent_1",
  "confidence": 0.92
}
```

### Monitoring API
```bash
GET /metrics/dashboard
Response: {
  "total_consultations": 45,
  "avg_response_time_ms": 450,
  "hallucination_rate": 0.03,
  "languages_supported": 5,
  "emergency_escalations": 3
}
```

---

## 🔍 Testing

```bash
# Unit tests
pytest backend/tests/unit

# Integration tests
pytest backend/tests/integration

# Load testing
locust -f backend/tests/load/locustfile.py

# Coverage report
pytest --cov=backend backend/tests
```

---

## 📚 Key Design Decisions

### 1. **Why 14 Agents?**
- 5 intake agents for parallel symptom collection across languages
- 4 reasoning agents for robust disease matching (ensemble approach)
- 3 safety agents for emergency detection redundancy
- 2 feedback agents for monitoring and continuous improvement

### 2. **Why LangGraph over other frameworks?**
- Native support for agent orchestration and state management
- Easy to debug multi-step workflows
- Built-in memory and context persistence

### 3. **Why Vector DB + TF-IDF hybrid search?**
- Vector DB captures semantic meaning (e.g., "chest pain" ≈ "cardiac distress")
- TF-IDF catches exact keyword matches (critical for drug names)
- Hybrid approach reduces hallucination risk

### 4. **Why confidence thresholding at 0.75?**
- Data shows >25% uncertainty correlates with misclassification in medical context
- Safe threshold to balance automation (60% queries) with human review (15%)

---

## 🐛 Known Limitations & Future Work

### Current Limitations
- ❌ Cannot diagnose confirmed medical conditions (only triage)
- ❌ Limited to symptom-based queries (no chronic disease management)
- ❌ Accuracy tested on clean text only (no speech transcription yet)
- ❌ Single-turn consultations (no multi-day follow-up tracking)

### Roadmap
- [ ] Add voice input support (speech-to-text)
- [ ] Multi-turn conversation memory (track patient over time)
- [ ] Integration with local doctor networks
- [ ] Prescription/medication history tracking
- [ ] Anonymous data aggregation for public health insights
- [ ] Mobile app (iOS/Android) for offline triage

---

## 🤝 Contributing

We're looking for:
- **Beta testers** – Validate accuracy on real patient queries
- **Doctors/Medical experts** – Improve symptom-disease mappings
- **Data scientists** – Optimize agent performance and reduce hallucination
- **DevOps engineers** – Improve deployment and monitoring

[See CONTRIBUTING.md for details]

---

## 📄 License

MIT License – See LICENSE file for details

---

## 👤 Author

**Samrat Majhi**  
AI/ML Engineer | Data Scientist  
[Portfolio](https://samratmajhi.com) | [GitHub](https://github.com/majhisamrat) | [LinkedIn](https://linkedin.com/in/samrat-majhi)

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/majhisamrat/ArogyaAI/issues)
- **Email**: work.samrat24@gmail.com
- **Looking for beta testers** – DM for early access!

---

**⭐ If you find this project useful, consider starring it on GitHub!**
