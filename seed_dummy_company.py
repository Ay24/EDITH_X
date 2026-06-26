import httpx
import time
import json

API_BASE = "http://localhost:8000"
AUTH_HEADER = {"Authorization": "Bearer demo-key"}

DUMMY_COMPANY_DOCS = [
    {
        "source": "HR-001: Employee Handbook",
        "metadata": {"department": "HR", "type": "policy", "confidentiality": "internal"},
        "content": (
            "Welcome to Apex Dynamics. Our core working hours are 10:00 AM to 3:00 PM EST. "
            "Employees are expected to be available for meetings during these hours. "
            "We offer unlimited PTO, but require a 2-week notice for any time off exceeding 5 consecutive days. "
            "Our primary health provider is BlueCross. Mental health days are fully supported and encouraged."
        )
    },
    {
        "source": "IT-SEC-04: Device Security Policy",
        "metadata": {"department": "IT", "type": "security", "confidentiality": "internal"},
        "content": (
            "All company-issued laptops must use FileVault (macOS) or BitLocker (Windows). "
            "Passwords must be at least 14 characters long and rotated every 90 days. "
            "Under no circumstances should production database credentials be stored in local text files or unencrypted vaults. "
            "Any lost device must be reported to the IT Helpdesk within 2 hours to initiate a remote wipe."
        )
    },
    {
        "source": "ENG-ARCH-01: Microservices Architecture",
        "metadata": {"department": "Engineering", "type": "architecture", "confidentiality": "internal"},
        "content": (
            "Our backend is divided into 14 microservices orchestrated via Kubernetes (EKS). "
            "Service-to-service communication happens over gRPC, while frontend clients consume REST endpoints via the Apollo API Gateway. "
            "The primary database for transactional data is PostgreSQL (Aurora), while vector embeddings are stored in Qdrant. "
            "All services must achieve 90% test coverage before CI/CD deployment to production."
        )
    },
    {
        "source": "FIN-Q3-2026: Quarterly Financial Summary",
        "metadata": {"department": "Finance", "type": "report", "confidentiality": "confidential"},
        "content": (
            "Q3 2026 Financial Highlights: Revenue reached $45.2M, a 12% increase from Q2. "
            "Cloud infrastructure costs rose by 15%, prompting the new 'Cost Optimization Initiative' (COI) led by the DevOps team. "
            "Net profit margin stands at 18%. The budget for Q4 marketing has been increased to $2.5M to support the launch of the new AI module."
        )
    },
    {
        "source": "PROD-ROADMAP-2026: Product Vision",
        "metadata": {"department": "Product", "type": "planning", "confidentiality": "internal"},
        "content": (
            "The main goal for Q4 2026 is the release of 'EDITH-X Enterprise'. "
            "Key features include a 4-layer cost firewall, LangGraph-based autonomous agents, and full RBAC integration. "
            "The launch is scheduled for November 15th. Marketing will start teasing the UI in late October."
        )
    },
    {
        "source": "SALES-PLAYBOOK-v3",
        "metadata": {"department": "Sales", "type": "guide", "confidentiality": "confidential"},
        "content": (
            "When pitching the Enterprise tier, focus on 'Cost Predictability'. "
            "Many CTOs are afraid of runaway LLM API bills. Emphasize our local-routing layer which offloads 60% of basic queries to local models, saving them thousands. "
            "Target buyer persona: VP of Engineering, CTO, or Head of AI. Avoid pitching to individual developers."
        )
    },
    {
        "source": "HR-002: Expense Reimbursement",
        "metadata": {"department": "HR", "type": "policy", "confidentiality": "internal"},
        "content": (
            "Expense reports must be submitted via Expensify by the 25th of each month. "
            "Daily food allowance for business travel is $85. Alcohol is not reimbursable unless entertaining a client. "
            "WFH stipend is $50/month for internet and $500 one-time for home office setup."
        )
    },
    {
        "source": "ENG-INC-001: Incident Response Plan",
        "metadata": {"department": "Engineering", "type": "runbook", "confidentiality": "internal"},
        "content": (
            "In the event of a SEV-1 (System Outage): "
            "1. The on-call engineer must open a Google Meet and link it in the #incident-response Slack channel. "
            "2. Notify the Director of Engineering if downtime exceeds 15 minutes. "
            "3. Do not attempt risky database migrations during an active outage without a second reviewer. "
            "4. Postmortem docs are required within 48 hours of resolution."
        )
    }
]

def seed_database():
    print(f"Connecting to EDITH-X API at {API_BASE}...")
    success_count = 0
    
    with httpx.Client(timeout=10.0) as client:
        # Check if API is up
        try:
            health = client.get(f"{API_BASE}/edith/v1/health")
            if health.status_code != 200:
                print("API is not healthy. Please start the API server.")
                return
        except Exception as e:
            print(f"Failed to connect to API: {e}")
            return
            
        print("API is online. Seeding documents...")
        
        for doc in DUMMY_COMPANY_DOCS:
            try:
                resp = client.post(
                    f"{API_BASE}/edith/v1/documents",
                    json=doc,
                    headers=AUTH_HEADER
                )
                if resp.status_code == 200:
                    print(f"[OK] Indexed: {doc['source']}")
                    success_count += 1
                else:
                    print(f"[ERROR] Failed to index {doc['source']}: {resp.text}")
            except Exception as e:
                print(f"[ERROR] Request failed for {doc['source']}: {e}")
                
            time.sleep(0.1) # slight delay to prevent overwhelming the server
            
    print(f"\nSeeding complete. {success_count}/{len(DUMMY_COMPANY_DOCS)} documents indexed successfully.")
    print("You can now test Retrieval Augmented Generation (RAG) queries in the EDITH-X Dashboard!")

if __name__ == "__main__":
    seed_database()
