from src.client.naukri_client import NaukriLoginClient
from src.client.job_client import NaukriJobClient
from src.models.models import Job
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = NaukriLoginClient(
    username=os.getenv("NAUKRI_USERNAME"),
    password=os.getenv("NAUKRI_PASSWORD")
)
client.login()

jc = NaukriJobClient(client)
job = Job(job_id="270426931746", title="Frontend Developer", company="Spes Manning", location="Pune", experience="2-5", salary="", posted_date="", apply_link="")

res = jc.apply_job(job, mandatory_skills=[], optional_skills=[], source="search")
print(json.dumps(res, indent=2))
