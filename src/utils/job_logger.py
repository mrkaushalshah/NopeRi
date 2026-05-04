import os
import json
from datetime import datetime

class JobLogger:
    def __init__(self, log_file="applied_jobs.json"):
        self.log_file = log_file
        self.applied_jobs = self._load_logs()

    def _load_logs(self):
        """Loads applied jobs from the log file."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not read {self.log_file}. Starting fresh.")
                return {}
        return {}

    def is_applied(self, job_id):
        """Checks if a job has already been applied to."""
        return str(job_id) in self.applied_jobs

    def log_apply(self, job_id, job_title, company):
        """Logs a successful application."""
        self.applied_jobs[str(job_id)] = {
            "title": job_title,
            "company": company,
            "applied_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_logs()

    def _save_logs(self):
        """Saves applied jobs to the log file."""
        try:
            with open(self.log_file, "w") as f:
                json.dump(self.applied_jobs, f, indent=4)
        except IOError as e:
            print(f"Error saving logs: {e}")

    def get_count(self):
        """Returns total number of applied jobs."""
        return len(self.applied_jobs)
