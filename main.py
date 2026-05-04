from src.client.naukri_client import NaukriLoginClient
from src.client.job_client import NaukriJobClient
from src.utils.ai_handler import AIHandler
from src.utils.job_logger import JobLogger
from dotenv import load_dotenv
from colorama import Fore, Style, init
import os
import time

load_dotenv()
init(autoreset=True)

if __name__ == "__main__":
    # ---------------------------------------------------------------
    # Load credentials from .env file
    # (NAUKRI_USERNAME and NAUKRI_PASSWORD must be set)
    # ---------------------------------------------------------------
    username = os.getenv("NAUKRI_USERNAME")
    password = os.getenv("NAUKRI_PASSWORD")

    # ---------------------------------------------------------------
    # 1. Login — authenticates and stores session + bearer token
    # ---------------------------------------------------------------
    client = NaukriLoginClient(username, password)
    client.login()
    # # ---------------------------------------------------------------
    # # 2. Resume upload — uploads a new PDF resume to your profile,provide the file path 
    # # ---------------------------------------------------------------
    # print(client.update_resume(r"C:/Users/HP/Downloads/my_resume2.pdf"))

    # # ---------------------------------------------------------------
    # # 3. Profile update — update headline and summary independently
    # #    Both fields are optional, pass only what you want to change
    # # ---------------------------------------------------------------
    # print(client.update_profile(headline="Software Engineer with 2.3 years of experience in backend development using Node.js, Python, AWS, SQL, and NoSQL."
    # ))

    # print(client.update_profile(summary="this is my summary"))

    # # ---------------------------------------------------------------
    # # 4. Misc — fetch profile ID and form key (mostly for debugging)
    # # ---------------------------------------------------------------
    # # print(client.fetch_profile_id())
    # # print(client.get_form_key2())

    # # ---------------------------------------------------------------
    # # 5. AI Handler — initialises the AI profile from your resume
    # # ---------------------------------------------------------------
    ai = AIHandler()
    ai.extract_profile() # Pre-extract profile data

    # # ---------------------------------------------------------------
    # # 6. Recommended jobs — fetches personalised job listings
    # #    based on your Naukri profile
    # # ---------------------------------------------------------------
    jc = NaukriJobClient(client, ai_handler=ai)
    # jobs = jc.get_recommended_jobs()

    # # ---------------------------------------------------------------
    # # 7. Job Logger — handles application persistence
    # # ---------------------------------------------------------------
    logger = JobLogger()

    print("Searching jobs...")    
    jobs = jc.search_jobs(keyword="Angular developer", location="Pune", experience=4, job_age=1)

    if not jobs:
        print(f"{Fore.YELLOW}  No jobs found.{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}Found {len(jobs)} jobs{Style.RESET_ALL}")

        success_count = 0
        skip_count = 0
        error_count = 0

        for job in jobs:
            print(f"\n{Fore.CYAN}{'-'*50}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  Title   : {Fore.YELLOW}{job.title}")
            print(f"{Fore.WHITE}  Company : {Fore.YELLOW}{job.company}")
            print(f"{Fore.WHITE}  Location: {Fore.YELLOW}{job.location}")
            print(f"{Fore.WHITE}  Job ID  : {Fore.YELLOW}{job.job_id}")

            if logger.is_applied(job.job_id):
                print(f"{Fore.BLUE}   [SKIP] Already applied previously.{Style.RESET_ALL}")
                skip_count += 1
                continue

            mandatory = job.tags[:2] if job.tags else []
            optional  = job.tags[2:] if len(job.tags) > 2 else []

            try:
                result = jc.apply_job(job, mandatory_skills=mandatory, optional_skills=optional, source="search")

                # Check questionnaire
                job_result = (result.get("jobs") or [{}])[0]
                if job_result.get("questionnaire"):
                    print(f"{Fore.YELLOW}   Questionnaire required. Solving with AI...{Style.RESET_ALL}")
                    
                    # Call the AI-powered questionnaire handler
                    q_result = jc.handle_ai_questionnaire_and_apply(
                        job, 
                        job_result["questionnaire"], 
                        sid="", 
                        mandatory_skills=mandatory, 
                        optional_skills=optional, 
                        source="search"
                    )
                    
                    if q_result.get("success") or (q_result.get("jobs") and q_result["jobs"][0].get("applyStatus")):
                        print(f"{Fore.GREEN}  [DONE] AI solved questionnaire and applied!{Style.RESET_ALL}")
                        logger.log_apply(job.job_id, job.title, job.company)
                        success_count += 1
                    else:
                        error_msg = q_result.get("error") or "Unknown AI error"
                        print(f"{Fore.RED}   AI Application failed: {error_msg}{Style.RESET_ALL}")
                        error_count += 1
                    continue

                if job_result.get("applyStatus") or result.get("status") == "success":
                    print(f"{Fore.GREEN}  [DONE] Applied successfully!{Style.RESET_ALL}")
                    logger.log_apply(job.job_id, job.title, job.company)
                    success_count += 1
                else:
                    print(f"{Fore.RED}   Application failed (unknown reason).{Style.RESET_ALL}")
                    error_count += 1

            except Exception as e:
                print(f"{Fore.RED}   Failed: {e}{Style.RESET_ALL}")
                error_count += 1
            
            time.sleep(5) 

        # ---------------------------------------------------------------
        # 8. Post-Run Summary
        # ---------------------------------------------------------------
        print(f"\n{Fore.MAGENTA}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}  RUN SUMMARY{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  Successful   : {success_count}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}  Skipped (Dup): {skip_count}{Style.RESET_ALL}")
        print(f"{Fore.RED}  Errors       : {error_count}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}  Total Applied: {logger.get_count()}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*50}{Style.RESET_ALL}")






    # --------------------------------------------------------------- 
    # 6. scrap the jobs,example
    #     
    # ---------------------------------------------------------------
    # i = 1
    # while True:
    #     job_list = jc.search_jobs("Node.js", location="Hyderabad", experience=1, page=i)
    #     for count, job in enumerate(job_list):
    #         print(count + 1, ":-", job.title, " :- ", job.company)
        
    #     breaker = input("enter anything for next page, q to quit: ")
    #     if breaker.strip().lower() == "q":
    #         break
    #     i += 1