"""Skill taxonomy and keyword-based skill extraction.

Each skill maps to a list of aliases. Aliases are matched as whole words, case-insensitively,
unless prefixed with "CS:" (case-sensitive, for short names like Go, R, C that are also
ordinary words or letters). Add skills freely; this list is the main thing to tune.
"""
from __future__ import annotations

import re

SKILLS: dict[str, dict[str, list[str]]] = {
    "Languages": {
        "Python": ["python"],
        "Java": ["java"],
        "JavaScript": ["javascript", "CS:JS"],
        "TypeScript": ["typescript"],
        "C++": ["c\\+\\+", "cpp"],
        "C": ["CS:C(?= ?[,/)]| (?:and|or|programming|language))", "CS:(?<=[(/])C(?![+#\\w])", "CS:(?<=, )C(?![+#\\w])"],
        "C#": ["c#", "\\.net", "dotnet"],
        "Go": ["golang", "CS:Go(?= ?[,/)]| (?:and|or|programming|language))"],
        "Rust": ["CS:Rust"],
        "Ruby": ["CS:Ruby"],
        "Kotlin": ["kotlin"],
        "Swift": ["CS:Swift"],
        "Scala": ["scala"],
        "R": ["CS:R(?![&\\-])"],
        "SQL": ["sql"],
        "Bash/Shell": ["bash", "shell scripting", "unix shell"],
        "MATLAB": ["matlab"],
    },
    "Web & Mobile": {
        "React": ["CS:React", "react\\.js", "reactjs"],
        "Node.js": ["node\\.js", "nodejs", "CS:Node"],
        "HTML/CSS": ["html", "css"],
        "Angular": ["CS:Angular"],
        "Vue": ["vue", "vue\\.js"],
        "Next.js": ["next\\.js", "nextjs"],
        "Django": ["django"],
        "Flask": ["flask"],
        "Spring": ["spring boot", "CS:Spring"],
        "Ruby on Rails": ["CS:Rails", "ruby on rails"],
        "REST APIs": ["CS:REST", "restful", "rest apis?"],
        "GraphQL": ["graphql"],
        "iOS": ["ios"],
        "Android": ["android"],
        "React Native": ["react native"],
    },
    "Data & ML": {
        "Machine Learning": ["machine learning", "CS:ML"],
        "Deep Learning": ["deep learning", "neural networks?"],
        "PyTorch": ["pytorch"],
        "TensorFlow": ["tensorflow"],
        "scikit-learn": ["scikit-learn", "sklearn"],
        "Pandas": ["pandas"],
        "NumPy": ["numpy"],
        "LLMs": ["llms?", "large language models?"],
        "NLP": ["nlp", "natural language processing"],
        "Computer Vision": ["computer vision"],
        "Statistics": ["statistics", "statistical"],
        "Spark": ["CS:Spark", "pyspark", "apache spark"],
        "Data Visualization": ["data visualization", "tableau", "looker", "power bi"],
        "Excel": ["CS:Excel", "microsoft excel"],
        "ETL / Data Pipelines": ["etl", "data pipelines?"],
        "Airflow": ["airflow"],
    },
    "Databases": {
        "PostgreSQL": ["postgres", "postgresql"],
        "MySQL": ["mysql"],
        "MongoDB": ["mongodb", "mongo"],
        "Redis": ["redis"],
        "NoSQL": ["nosql"],
        "Snowflake": ["snowflake"],
        "BigQuery": ["bigquery"],
    },
    "Cloud & DevOps": {
        "AWS": ["aws", "amazon web services"],
        "GCP": ["gcp", "google cloud"],
        "Azure": ["azure"],
        "Docker": ["docker", "containers?", "containerization"],
        "Kubernetes": ["kubernetes", "k8s"],
        "Terraform": ["terraform"],
        "CI/CD": ["ci/cd", "continuous integration", "continuous delivery", "github actions", "jenkins"],
        "Linux": ["linux", "unix"],
        "Git": ["git", "github", "version control"],
        "Microservices": ["microservices?"],
        "Kafka": ["kafka"],
    },
    "CS Fundamentals": {
        "Data Structures & Algorithms": ["data structures", "algorithms"],
        "Distributed Systems": ["distributed systems?"],
        "Operating Systems": ["operating systems?"],
        "Networking": ["networking", "tcp/ip"],
        "Object-Oriented Programming": ["object[- ]oriented", "CS:OOP"],
        "System Design": ["system design", "systems design"],
        "Testing": ["unit tests?", "unit testing", "testing frameworks?", "test-driven"],
        "Security": ["cybersecurity", "(?:information|application|network|cloud|product|computer) security", "security engineering", "secure coding"],
    },
    "AI Engineering": {
        "Generative AI": ["generative ai", "genai", "gen ai"],
        "RAG": ["CS:RAG", "retrieval[- ]augmented"],
        "Prompt Engineering": ["prompt engineering", "prompting", "prompt design"],
        "LLM APIs": ["openai api", "anthropic api", "claude api", "gpt-?4\\w*", "llm apis?"],
        "LangChain / LlamaIndex": ["langchain", "langgraph", "llamaindex", "llama index"],
        "AI Agents": ["ai agents?", "agentic", "llm agents?", "tool use"],
        "Vector Databases": ["vector (?:databases?|stores?|search)", "embeddings?", "pinecone", "pgvector", "faiss"],
        "Fine-tuning": ["fine-?tun\\w*", "rlhf", "lora"],
        "Model Evaluation": ["evals?", "model evaluation", "evaluation frameworks?"],
        "Hugging Face": ["hugging ?face", "transformers library"],
        "MLOps": ["mlops", "ml ops", "model deployment", "deploy(?:ing)? models?", "mlflow", "model monitoring", "kubeflow"],
        "SageMaker / Vertex / Azure ML": ["sagemaker", "vertex ai", "azure ml", "azure machine learning", "bedrock", "azure openai"],
        "Feature Engineering": ["feature engineering"],
        "A/B Testing / Experimentation": ["a/b test\\w*", "experimentation", "experiment design", "causal inference"],
        "Forecasting / Optimization": ["forecasting", "time series", "optimization models?", "operations research"],
        "dbt": ["CS:dbt"],
    },
    "Consulting & Business": {
        "Client-Facing": ["client[- ]facing", "customer[- ]facing", "work(?:ing)? (?:directly )?with (?:clients|customers)", "client engagements?"],
        "Stakeholder Management": ["stakeholders?"],
        "Presenting to Executives": ["present(?:ing|ations?)? to (?:executives|leadership|stakeholders|clients)", "executive presentations?", "data storytelling"],
        "Requirements Gathering": ["requirements gathering", "gather(?:ing)? requirements", "business requirements", "scoping"],
        "Business Acumen": ["business acumen", "business impact", "business problems?", "roi"],
        "Solution Architecture": ["solutions? architecture", "solutions? design", "technical solutions?"],
        "Product Sense": ["product sense", "product thinking", "product intuition"],
        "PowerPoint / Slides": ["powerpoint", "google slides", "CS:Keynote"],
    },
    "Professional": {  # soft skills: reported separately, not counted in match scores
        "Communication": ["communication skills", "communicate (?:clearly|effectively)", "written and verbal"],
        "Collaboration": ["collaborat\\w*", "teamwork", "cross-functional"],
        "Problem Solving": ["problem[- ]solving"],
        "Agile": ["agile", "scrum"],
    },
}


def _compile(alias: str) -> re.Pattern:
    flags = 0
    if alias.startswith("CS:"):
        alias = alias[3:]
    else:
        flags = re.IGNORECASE
    # Custom word boundaries so aliases like "c++" and ".net" still work.
    return re.compile(rf"(?<![\w.+#]){alias}(?![\w+#])", flags)


PATTERNS: dict[str, list[re.Pattern]] = {
    skill: [_compile(a) for a in aliases]
    for group in SKILLS.values()
    for skill, aliases in group.items()
}
CATEGORY = {skill: cat for cat, group in SKILLS.items() for skill in group}
SOFT_SKILLS = set(SKILLS["Professional"])


def extract_skills(text: str) -> set[str]:
    return {skill for skill, pats in PATTERNS.items() if any(p.search(text) for p in pats)}


def normalize(name: str) -> str | None:
    """Map a user-written skill (e.g. 'react.js', 'postgres') to its canonical name, if known."""
    name = name.strip()
    for skill in PATTERNS:
        if skill.lower() == name.lower():
            return skill
    found = extract_skills(name)
    return next(iter(found)) if len(found) == 1 else None
