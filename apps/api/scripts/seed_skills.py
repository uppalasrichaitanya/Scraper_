"""
seed_skills.py — Seed the canonical skill taxonomy into the skills table.

~500 skills across languages, frameworks, databases, cloud, tools, soft skills.
Each entry has a canonical name + list of aliases the skill_extractor uses
for NER matching in job descriptions.

Run AFTER alembic upgrade head:
  python scripts/seed_skills.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow imports from apps/api
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from models.skill import Skill

# ─────────────────────────────────────────────────────────────────────────────
# Skill taxonomy
# Format: (canonical_name, category, [aliases])
# ─────────────────────────────────────────────────────────────────────────────
SKILLS: list[tuple[str, str, list[str]]] = [
    # ── Programming Languages ─────────────────────────────────────────────────
    ("Python", "language", ["python3", "py", "python2"]),
    ("JavaScript", "language", ["js", "javascript", "node.js", "nodejs", "node"]),
    ("TypeScript", "language", ["ts", "typescript"]),
    ("Java", "language", ["java8", "java11", "java17", "java21"]),
    ("Kotlin", "language", ["kotlin", "kt"]),
    ("Scala", "language", ["scala"]),
    ("Go", "language", ["golang", "go-lang"]),
    ("Rust", "language", ["rust-lang"]),
    ("C", "language", ["c programming", "c language"]),
    ("C++", "language", ["cpp", "c plus plus", "c++"]),
    ("C#", "language", ["csharp", "c sharp", "dotnet c#"]),
    ("Ruby", "language", ["rb", "ruby on rails language"]),
    ("PHP", "language", ["php7", "php8"]),
    ("Swift", "language", ["swift5"]),
    ("Objective-C", "language", ["objc", "objective c"]),
    ("R", "language", ["r-lang", "r language", "rlang"]),
    ("MATLAB", "language", ["matlab"]),
    ("Perl", "language", ["perl5"]),
    ("Shell", "language", ["bash", "zsh", "sh", "shell scripting", "bash scripting"]),
    ("Lua", "language", ["lua5"]),
    ("Haskell", "language", ["haskell"]),
    ("Elixir", "language", ["elixir"]),
    ("Erlang", "language", ["erlang"]),
    ("Clojure", "language", ["clojure"]),
    ("F#", "language", ["fsharp", "f sharp"]),
    ("Dart", "language", ["dart"]),
    ("Solidity", "language", ["solidity"]),

    # ── Web Frameworks ────────────────────────────────────────────────────────
    ("React", "framework", ["reactjs", "react.js", "react js"]),
    ("Next.js", "framework", ["nextjs", "next js"]),
    ("Vue.js", "framework", ["vue", "vuejs", "vue js"]),
    ("Nuxt.js", "framework", ["nuxt", "nuxtjs"]),
    ("Angular", "framework", ["angularjs", "angular2", "angular 2+"]),
    ("Svelte", "framework", ["sveltejs", "svelte js", "sveltekit"]),
    ("SvelteKit", "framework", ["svelte kit"]),
    ("Remix", "framework", ["remix run"]),
    ("Astro", "framework", ["astro.js", "astrojs"]),
    ("Express.js", "framework", ["express", "expressjs"]),
    ("Fastify", "framework", ["fastify"]),
    ("NestJS", "framework", ["nest.js", "nestjs"]),
    ("Django", "framework", ["django rest framework", "drf"]),
    ("FastAPI", "framework", ["fast api", "fastapi"]),
    ("Flask", "framework", ["flask python", "flask api"]),
    ("Spring Boot", "framework", ["spring", "spring framework", "springboot"]),
    ("Rails", "framework", ["ruby on rails", "ror"]),
    ("Laravel", "framework", ["laravel php"]),
    ("Symfony", "framework", ["symfony php"]),
    ("ASP.NET", "framework", ["asp.net core", "aspnet", "asp net"]),
    ("Phoenix", "framework", ["phoenix framework", "elixir phoenix"]),
    ("Gin", "framework", ["gin-gonic", "gin framework"]),
    ("Echo", "framework", ["echo go", "echo framework"]),
    ("Fiber", "framework", ["fiber go"]),

    # ── Mobile ────────────────────────────────────────────────────────────────
    ("React Native", "mobile", ["react-native", "rn"]),
    ("Flutter", "mobile", ["flutter dart"]),
    ("Android", "mobile", ["android development", "android sdk"]),
    ("iOS", "mobile", ["ios development", "ios sdk"]),
    ("Expo", "mobile", ["expo go"]),
    ("Ionic", "mobile", ["ionic framework"]),

    # ── Databases – Relational ────────────────────────────────────────────────
    ("PostgreSQL", "database", ["postgres", "psql", "postgresql 14", "postgresql 15", "postgresql 16"]),
    ("MySQL", "database", ["mysql 8", "mysql database"]),
    ("MariaDB", "database", ["mariadb"]),
    ("SQLite", "database", ["sqlite3"]),
    ("Oracle DB", "database", ["oracle database", "oracle sql", "oracle"]),
    ("Microsoft SQL Server", "database", ["mssql", "sql server", "t-sql", "tsql"]),

    # ── Databases – NoSQL ─────────────────────────────────────────────────────
    ("MongoDB", "database", ["mongo", "mongodb atlas"]),
    ("Cassandra", "database", ["apache cassandra"]),
    ("DynamoDB", "database", ["aws dynamodb", "dynamodb"]),
    ("Redis", "database", ["redis cache", "redis pub/sub"]),
    ("Elasticsearch", "database", ["elastic", "opensearch", "es"]),
    ("CouchDB", "database", ["couchdb"]),
    ("Neo4j", "database", ["neo4j", "graph database"]),
    ("InfluxDB", "database", ["influxdb", "time series db"]),
    ("Firestore", "database", ["firebase firestore", "cloud firestore"]),

    # ── Cloud Platforms ───────────────────────────────────────────────────────
    ("AWS", "cloud", ["amazon web services", "aws cloud", "amazon aws"]),
    ("GCP", "cloud", ["google cloud platform", "google cloud", "google gcp"]),
    ("Azure", "cloud", ["microsoft azure", "azure cloud"]),
    ("DigitalOcean", "cloud", ["digital ocean", "do cloud"]),
    ("Vercel", "cloud", ["vercel platform"]),
    ("Netlify", "cloud", ["netlify platform"]),
    ("Heroku", "cloud", ["heroku platform"]),
    ("Fly.io", "cloud", ["fly io"]),
    ("Cloudflare", "cloud", ["cloudflare workers", "cloudflare pages"]),
    ("Render", "cloud", ["render.com"]),

    # ── AWS Services ──────────────────────────────────────────────────────────
    ("Amazon EC2", "cloud", ["ec2", "aws ec2"]),
    ("Amazon S3", "cloud", ["s3", "aws s3"]),
    ("Amazon RDS", "cloud", ["rds", "aws rds"]),
    ("Amazon Lambda", "cloud", ["aws lambda", "lambda function"]),
    ("Amazon ECS", "cloud", ["ecs", "aws ecs"]),
    ("Amazon EKS", "cloud", ["eks", "aws eks"]),
    ("Amazon SQS", "cloud", ["sqs", "aws sqs"]),
    ("Amazon SNS", "cloud", ["sns", "aws sns"]),
    ("Amazon CloudFront", "cloud", ["cloudfront", "aws cloudfront"]),
    ("Amazon Bedrock", "cloud", ["aws bedrock"]),

    # ── DevOps / Infrastructure ───────────────────────────────────────────────
    ("Docker", "devops", ["docker container", "containerization", "dockerfile"]),
    ("Kubernetes", "devops", ["k8s", "kube", "kubectl"]),
    ("Terraform", "devops", ["terraform iac", "hashicorp terraform"]),
    ("Ansible", "devops", ["ansible playbook"]),
    ("Helm", "devops", ["helm charts", "kubernetes helm"]),
    ("GitHub Actions", "devops", ["gha", "github ci"]),
    ("GitLab CI", "devops", ["gitlab cicd", "gitlab pipelines"]),
    ("Jenkins", "devops", ["jenkins ci", "jenkins pipeline"]),
    ("CircleCI", "devops", ["circle ci"]),
    ("ArgoCD", "devops", ["argo cd", "argocd"]),
    ("Pulumi", "devops", ["pulumi iac"]),
    ("Nginx", "devops", ["nginx server", "nginx proxy"]),
    ("Apache", "devops", ["apache httpd", "apache server"]),
    ("Prometheus", "devops", ["prometheus monitoring"]),
    ("Grafana", "devops", ["grafana dashboard"]),
    ("Datadog", "devops", ["datadog monitoring", "dd-agent"]),
    ("New Relic", "devops", ["newrelic"]),
    ("Sentry", "devops", ["sentry error tracking"]),
    ("OpenTelemetry", "devops", ["otel", "open telemetry"]),

    # ── Message Queues ────────────────────────────────────────────────────────
    ("Kafka", "messaging", ["apache kafka", "kafka streams", "confluent kafka"]),
    ("RabbitMQ", "messaging", ["rabbit mq", "rabbitmq"]),
    ("Celery", "messaging", ["celery task queue"]),
    ("Redis Streams", "messaging", ["redis stream"]),
    ("Amazon Kinesis", "messaging", ["kinesis", "aws kinesis"]),
    ("Pub/Sub", "messaging", ["google pub/sub", "pubsub"]),
    ("NATS", "messaging", ["nats.io"]),

    # ── ML / AI ───────────────────────────────────────────────────────────────
    ("Machine Learning", "ml", ["ml", "machine-learning"]),
    ("Deep Learning", "ml", ["dl", "neural networks"]),
    ("TensorFlow", "ml", ["tf", "tensorflow 2"]),
    ("PyTorch", "ml", ["torch", "pytorch"]),
    ("Scikit-learn", "ml", ["sklearn", "scikit learn"]),
    ("Keras", "ml", ["keras api"]),
    ("Hugging Face", "ml", ["huggingface", "transformers"]),
    ("LangChain", "ml", ["langchain"]),
    ("OpenAI API", "ml", ["openai", "gpt api", "chatgpt api"]),
    ("Computer Vision", "ml", ["cv", "image recognition"]),
    ("NLP", "ml", ["natural language processing", "text analysis"]),
    ("MLflow", "ml", ["ml flow"]),
    ("Kubeflow", "ml", ["kubeflow pipelines"]),
    ("XGBoost", "ml", ["xgboost", "gradient boosting"]),
    ("LightGBM", "ml", ["lightgbm", "lgbm"]),
    ("ONNX", "ml", ["onnx runtime"]),
    ("spaCy", "ml", ["spacy nlp"]),
    ("NLTK", "ml", ["natural language toolkit"]),

    # ── Data Engineering ──────────────────────────────────────────────────────
    ("Apache Spark", "data", ["spark", "pyspark", "spark sql"]),
    ("Apache Flink", "data", ["flink", "apache flink"]),
    ("Apache Airflow", "data", ["airflow", "airflow dags"]),
    ("dbt", "data", ["dbt core", "data build tool"]),
    ("Pandas", "data", ["pandas python", "pandas df"]),
    ("NumPy", "data", ["numpy", "np"]),
    ("Polars", "data", ["polars dataframe"]),
    ("Dask", "data", ["dask parallel"]),
    ("Snowflake", "data", ["snowflake db", "snowflake data warehouse"]),
    ("BigQuery", "data", ["google bigquery", "bq"]),
    ("Redshift", "data", ["amazon redshift", "aws redshift"]),
    ("Databricks", "data", ["databricks platform"]),
    ("Delta Lake", "data", ["delta lake", "deltalake"]),
    ("Great Expectations", "data", ["great expectations", "ge"]),
    ("dlt", "data", ["data load tool"]),
    ("Prefect", "data", ["prefect io", "prefect 2"]),

    # ── Security ──────────────────────────────────────────────────────────────
    ("OAuth2", "security", ["oauth 2", "oauth2.0", "oidc"]),
    ("JWT", "security", ["json web token", "jwt authentication"]),
    ("SSL/TLS", "security", ["ssl", "tls", "https"]),
    ("OWASP", "security", ["owasp top 10"]),
    ("Penetration Testing", "security", ["pentest", "pen testing", "ethical hacking"]),
    ("SAST", "security", ["static analysis security", "sonarqube"]),
    ("DAST", "security", ["dynamic analysis security"]),
    ("Vault", "security", ["hashicorp vault", "secrets management"]),
    ("RBAC", "security", ["role based access control"]),

    # ── Frontend / UI ─────────────────────────────────────────────────────────
    ("HTML", "frontend", ["html5", "html 5", "hypertext markup"]),
    ("CSS", "frontend", ["css3", "css 3", "stylesheets"]),
    ("Sass", "frontend", ["scss", "sass css"]),
    ("Tailwind CSS", "frontend", ["tailwind", "tailwindcss"]),
    ("Material UI", "frontend", ["mui", "material-ui"]),
    ("Ant Design", "frontend", ["antd", "ant design"]),
    ("Chakra UI", "frontend", ["chakra"]),
    ("Shadcn/UI", "frontend", ["shadcn", "shadcn ui"]),
    ("GraphQL", "frontend", ["graphql api", "gql"]),
    ("REST API", "frontend", ["restful api", "rest", "rest api", "restful"]),
    ("WebSockets", "frontend", ["websocket", "ws", "wss"]),
    ("gRPC", "frontend", ["grpc", "protobuf", "protocol buffers"]),
    ("Three.js", "frontend", ["threejs", "three js", "webgl"]),
    ("D3.js", "frontend", ["d3js", "d3 data"]),

    # ── Testing ───────────────────────────────────────────────────────────────
    ("Jest", "testing", ["jest testing", "jest js"]),
    ("Vitest", "testing", ["vitest js"]),
    ("Cypress", "testing", ["cypress e2e", "cypress testing"]),
    ("Playwright", "testing", ["playwright testing", "playwright e2e"]),
    ("Pytest", "testing", ["pytest python", "pytest"]),
    ("JUnit", "testing", ["junit 5", "junit testing"]),
    ("Selenium", "testing", ["selenium webdriver"]),
    ("Testing Library", "testing", ["react testing library", "rtl"]),
    ("k6", "testing", ["k6 load testing"]),
    ("Locust", "testing", ["locust load test"]),

    # ── Version Control / Collaboration ──────────────────────────────────────
    ("Git", "tools", ["git version control", "github", "gitlab", "bitbucket"]),
    ("GitHub", "tools", ["github.com"]),
    ("GitLab", "tools", ["gitlab.com"]),
    ("Bitbucket", "tools", ["bitbucket git"]),
    ("Jira", "tools", ["jira software", "atlassian jira"]),
    ("Confluence", "tools", ["atlassian confluence"]),
    ("Slack", "tools", ["slack messaging"]),
    ("Linear", "tools", ["linear app"]),
    ("Notion", "tools", ["notion app"]),
    ("Figma", "tools", ["figma design"]),

    # ── Methodologies ─────────────────────────────────────────────────────────
    ("Agile", "methodology", ["agile development", "agile methodology"]),
    ("Scrum", "methodology", ["scrum framework", "scrum master"]),
    ("Kanban", "methodology", ["kanban board"]),
    ("TDD", "methodology", ["test driven development", "test-driven"]),
    ("BDD", "methodology", ["behavior driven development", "behaviour-driven"]),
    ("CI/CD", "methodology", ["continuous integration", "continuous deployment", "cicd"]),
    ("DevOps", "methodology", ["devops culture", "devops practices"]),
    ("MLOps", "methodology", ["ml ops", "ml operations"]),
    ("Platform Engineering", "methodology", ["platform eng"]),
    ("Site Reliability Engineering", "methodology", ["sre", "reliability engineering"]),
    ("Microservices", "methodology", ["microservice architecture", "micro services"]),
    ("Event-Driven Architecture", "methodology", ["eda", "event driven", "event sourcing"]),
    ("Domain-Driven Design", "methodology", ["ddd", "domain driven"]),

    # ── Soft Skills ───────────────────────────────────────────────────────────
    ("Communication", "soft", ["written communication", "verbal communication"]),
    ("Leadership", "soft", ["team leadership", "tech lead"]),
    ("Problem Solving", "soft", ["problem-solving", "analytical thinking"]),
    ("Mentoring", "soft", ["mentorship", "coaching"]),
    ("Code Review", "soft", ["code reviews", "pr review"]),
    ("System Design", "soft", ["systems design", "architecture design", "high level design"]),
    ("Technical Writing", "soft", ["documentation", "tech documentation"]),

    # ── ERP / Business Software ───────────────────────────────────────────────
    ("SAP", "enterprise", ["sap erp", "sap s/4hana", "sap hana"]),
    ("Salesforce", "enterprise", ["sfdc", "salesforce crm"]),
    ("Workday", "enterprise", ["workday hcm"]),
    ("ServiceNow", "enterprise", ["service now"]),
    ("Tableau", "enterprise", ["tableau desktop", "tableau server"]),
    ("Power BI", "enterprise", ["powerbi", "microsoft power bi"]),
    ("Looker", "enterprise", ["looker studio", "google looker"]),
    ("Metabase", "enterprise", ["metabase bi"]),
    ("Superset", "enterprise", ["apache superset"]),

    # ── Networking / Infra ────────────────────────────────────────────────────
    ("TCP/IP", "networking", ["tcp ip", "networking protocols"]),
    ("DNS", "networking", ["dns configuration"]),
    ("Load Balancing", "networking", ["load balancer", "haproxy"]),
    ("VPN", "networking", ["wireguard", "openvpn"]),
    ("CDN", "networking", ["content delivery network", "cdn"]),
    ("Service Mesh", "networking", ["istio", "linkerd", "envoy proxy"]),
]


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # Clear existing skills to allow idempotent re-seeding
        await session.execute(delete(Skill))

        for name, category, aliases in SKILLS:
            skill = Skill(name=name, category=category, aliases=aliases)
            session.add(skill)

        await session.commit()
        print(f"[OK] Seeded {len(SKILLS)} canonical skills into the skills table.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
