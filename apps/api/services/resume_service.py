"""
services/resume_service.py — Resume upload, text extraction, LLM parsing, skill normalization.

Flow:
  1. User uploads PDF/DOCX → stored locally (or S3)
  2. Text extracted via pdfplumber / python-docx
  3. Structured data extracted via OpenAI GPT-4o-mini (or mock for dev)
  4. Skills normalized through alias map
  5. Embedding generated from profile text
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Skill normalization alias map ─────────────────────────────────────────────
# Maps common variations to a canonical lowercase form.
SKILL_ALIASES: dict[str, str] = {
    "react.js": "react",
    "reactjs": "react",
    "react js": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "vue js": "vue",
    "node.js": "nodejs",
    "node js": "nodejs",
    "next.js": "nextjs",
    "next js": "nextjs",
    "nuxt.js": "nuxtjs",
    "express.js": "expressjs",
    "angular.js": "angularjs",
    "angularjs": "angular",
    "typescript": "typescript",
    "type script": "typescript",
    "java script": "javascript",
    "js": "javascript",
    "py": "python",
    "python3": "python",
    "python 3": "python",
    "golang": "go",
    "c++": "cpp",
    "c #": "csharp",
    "c#": "csharp",
    "dot net": "dotnet",
    ".net": "dotnet",
    "asp.net": "dotnet",
    "mongo db": "mongodb",
    "mongo": "mongodb",
    "postgres": "postgresql",
    "pg": "postgresql",
    "mysql": "mysql",
    "ms sql": "mssql",
    "sql server": "mssql",
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "k8s": "kubernetes",
    "docker compose": "docker",
    "ci/cd": "cicd",
    "ci cd": "cicd",
    "machine learning": "ml",
    "deep learning": "dl",
    "artificial intelligence": "ai",
    "natural language processing": "nlp",
    "scikit-learn": "sklearn",
    "scikit learn": "sklearn",
    "tensorflow": "tensorflow",
    "tensor flow": "tensorflow",
    "pytorch": "pytorch",
    "py torch": "pytorch",
}


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize a list of skills using the alias map. Returns deduplicated lowercase list."""
    normalized = set()
    for skill in skills:
        s = skill.strip().lower()
        s = SKILL_ALIASES.get(s, s)
        if s:
            normalized.add(s)
    return sorted(normalized)


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using pdfplumber."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route to the correct extractor based on file extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Only PDF and DOCX are supported.")


# ── LLM-based structured extraction ──────────────────────────────────────────

EXTRACTION_PROMPT = """Extract structured data from this resume. Return ONLY valid JSON, no markdown fences.

Schema:
{{
  "current_title": "most recent job title",
  "years_experience": <integer, total years>,
  "skills": ["skill1", "skill2", ...],
  "education": [{{"degree": "", "field": "", "institution": "", "year": null}}],
  "experience": [{{"title": "", "company": "", "duration_years": 0.0, "summary": ""}}]
}}

If a field cannot be determined, use null for strings/integers and [] for arrays.

Resume text:
{resume_text}"""


async def parse_resume_with_llm(resume_text: str) -> dict[str, Any]:
    """Send resume text to OpenAI GPT-4o-mini for structured extraction.
    
    Falls back to a basic regex-based extraction if no API key is configured.
    """
    from core.config import settings

    if not settings.OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY — using basic regex extraction fallback")
        return _basic_extraction_fallback(resume_text)

    try:
        import openai
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a resume parser. Extract structured data accurately."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(resume_text=resume_text[:4000])},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        
        return json.loads(content)
    except Exception as e:
        logger.error("LLM extraction failed: %s — falling back to basic extraction", e)
        return _basic_extraction_fallback(resume_text)


def _basic_extraction_fallback(text: str) -> dict[str, Any]:
    """Regex-based fallback when no LLM is available.
    
    Extracts skills by matching against a known list. Very basic but functional.
    """
    known_skills = [
        "python", "javascript", "typescript", "java", "go", "rust", "ruby",
        "react", "angular", "vue", "nextjs", "django", "flask", "fastapi",
        "nodejs", "express", "spring", "docker", "kubernetes", "aws", "gcp",
        "azure", "postgresql", "mongodb", "redis", "elasticsearch", "git",
        "linux", "sql", "graphql", "rest", "api", "html", "css", "sass",
        "terraform", "ansible", "jenkins", "github", "gitlab", "jira",
        "figma", "pandas", "numpy", "tensorflow", "pytorch", "sklearn",
    ]
    
    text_lower = text.lower()
    found_skills = [s for s in known_skills if s in text_lower]
    
    return {
        "current_title": None,
        "years_experience": None,
        "skills": found_skills,
        "education": [],
        "experience": [],
    }


# ── File storage ──────────────────────────────────────────────────────────────

def store_resume_file(user_id: str, file_bytes: bytes, ext: str) -> str:
    """Store resume file. Uses local uploads/ dir for dev, S3 for production.
    
    Returns the storage key (local path or S3 key).
    """
    from core.config import settings

    s3_key = f"users/{user_id}/resume{ext}"

    if settings.AWS_ACCESS_KEY_ID:
        # S3 upload
        try:
            import boto3
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            s3.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=s3_key,
                Body=file_bytes,
                ContentType="application/octet-stream",
            )
            logger.info("Resume uploaded to S3: %s/%s", settings.AWS_S3_BUCKET, s3_key)
            return f"s3://{settings.AWS_S3_BUCKET}/{s3_key}"
        except Exception as e:
            logger.error("S3 upload failed: %s — falling back to local storage", e)

    # Local fallback
    upload_dir = Path("uploads/resumes") / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    local_path = upload_dir / f"resume{ext}"
    local_path.write_bytes(file_bytes)
    logger.info("Resume stored locally: %s", local_path)
    return str(local_path)
