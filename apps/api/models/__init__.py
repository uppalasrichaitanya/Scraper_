from .base import Base
from .user import User, UserProfile, ConsentRecord
from .company import Company, Location
from .job import Job, JobVersion
from .skill import Skill, JobSkill
from .crawler import CrawlRun, CrawlError
from .saved import SavedJob, JobAlert
from .embedding import JobEmbedding

__all__ = [
    "Base",
    "User",
    "UserProfile",
    "ConsentRecord",
    "Company",
    "Location",
    "Job",
    "JobVersion",
    "Skill",
    "JobSkill",
    "CrawlRun",
    "CrawlError",
    "SavedJob",
    "JobAlert",
    "JobEmbedding",
]
