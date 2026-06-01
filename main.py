from src.client.naukri_client import NaukriLoginClient
from src.client.job_client import NaukriJobClient
from src.utils.ai_handler import AIHandler
from src.utils.job_logger import JobLogger
from src.client.jop_classifier import JobFilterPipeline2
from src.exceptions.exceptions import NaukriAuthError
from dotenv import load_dotenv
from colorama import Fore, Style, init
import os
import time
import asyncio
import re
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()
init(autoreset=True)

pending_jobs = {}

# Global instances so they can be accessed in callbacks
jc = None
logger = None

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, job_id = data.split(":", 1)
    
    if action == "apply":
        if job_id not in pending_jobs:
            await query.edit_message_text(text="❌ Job no longer found in pending queue.")
            return
            
        job = pending_jobs[job_id]
        mandatory = job.tags[:2] if job.tags else []
        optional  = job.tags[2:] if len(job.tags) > 2 else []
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                result = await jc.apply_job(job, mandatory_skills=mandatory, optional_skills=optional, source="search")
                job_result = (result.get("jobs") or [{}])[0]
                
                # Helper to check if already applied
                def check_already_applied(res):
                    res_str = str(res).upper()
                    return "ALREADY_APPLIED" in res_str or ("ALREADY" in res_str and "APPLIED" in res_str)

                if check_already_applied(result):
                    logger.log_apply(job.job_id, job.title, job.company)
                    await query.edit_message_text(text="✅ Already Applied previously! (Logged and cleared)")
                    if job_id in pending_jobs:
                        del pending_jobs[job_id]
                    return

                if job_result.get("questionnaire"):
                    q_result = await jc.handle_ai_questionnaire_and_apply(
                        job, 
                        job_result["questionnaire"], 
                        sid="", 
                        mandatory_skills=mandatory, 
                        optional_skills=optional, 
                        source="search"
                    )
                    
                    if check_already_applied(q_result):
                        logger.log_apply(job.job_id, job.title, job.company)
                        await query.edit_message_text(text="✅ Already Applied previously! (Logged and cleared)")
                        if job_id in pending_jobs:
                            del pending_jobs[job_id]
                        return

                    q_success = False
                    if q_result.get("status") == "success":
                        q_success = True
                    elif "applyStatus" in q_result and str(job.job_id) in q_result.get("applyStatus", {}):
                        q_success = True
                    elif (q_result.get("jobs") or [{}])[0].get("applyStatus"):
                        q_success = True

                    if q_success:
                        logger.log_apply(job.job_id, job.title, job.company)
                        
                        q_text = "✅ *Applied! (AI solved questionnaire)*\n\n*Q&A:*\n"
                        q_list = q_result.get("questionnaire", [])
                        ai_ans = q_result.get("ai_answers", {})
                        
                        for q in q_list:
                            q_id = str(q.get("questionId", ""))
                            q_title = q.get("questionName", "Unknown question")
                            
                            # Strip HTML tags
                            q_title = re.sub(r'<[^>]+>', '', q_title).strip()
                            
                            ans_key = str(ai_ans.get(q_id, "No answer provided"))
                            
                            # Map answer key to text if it's a multiple choice
                            options = q.get("answerOption")
                            ans_val = ans_key
                            if isinstance(options, dict) and ans_key in options:
                                ans_val = options[ans_key]
                            elif isinstance(options, list):
                                for opt in options:
                                    if isinstance(opt, dict) and str(opt.get("id")) == ans_key:
                                        ans_val = opt.get("value", ans_key)
                                        break
                                        
                            q_text += f"🔹 *{q_title}*\n  ↳ _{ans_val}_\n\n"

                        if len(q_text) > 4000:
                            q_text = q_text[:4000] + "...(truncated)"
                            
                        await query.edit_message_text(text=q_text, parse_mode='Markdown')
                    else:
                        await query.edit_message_text(text=f"❌ Application failed: {q_result.get('error') or 'Unknown error'}")
                else:
                    is_success = False
                    if result.get("status") == "success":
                        is_success = True
                    elif "applyStatus" in result and str(job.job_id) in result.get("applyStatus", {}):
                        is_success = True
                    elif job_result.get("applyStatus"):
                        is_success = True

                    if is_success:
                        logger.log_apply(job.job_id, job.title, job.company)
                        await query.edit_message_text(text="✅ Applied successfully!")
                    else:
                        await query.edit_message_text(text="❌ Application failed (unknown reason).")
                
                # If we reached here, success or handled error
                break

            except NaukriAuthError:
                if attempt < max_retries - 1:
                    print(f"{Fore.YELLOW}Session expired. Attempting auto-login (attempt {attempt+1}/{max_retries})...{Style.RESET_ALL}")
                    await query.edit_message_text(text="🔄 Session expired. Auto-logging in and retrying...")
                    try:
                        await jc._client.login()
                        # Next iteration will retry the application
                    except Exception as login_e:
                        print(f"{Fore.RED}Auto-login failed: {login_e}{Style.RESET_ALL}")
                        await query.edit_message_text(text=f"❌ Session expired. Re-login failed: {login_e}")
                        return
                else:
                    await query.edit_message_text(text="❌ Session expired. Auto-login failed after retry. Please check credentials.")
                    return
            except Exception as e:
                await query.edit_message_text(text=f"❌ Failed: {e}")
                return
            
        if job_id in pending_jobs:
            del pending_jobs[job_id]
            
    elif action == "skip":
        await query.edit_message_text(text="❌ Skipped")
        if job_id in pending_jobs:
            del pending_jobs[job_id]


async def job_search_loop(app: ApplicationBuilder):
    global jc, logger
    bot = app.bot if app else None
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    while True:
        try:
            queries = [
                {"keyword": "Software developer", "location": "Pune"},
                {"keyword": "Senior Software developer", "location": "Pune"},
                {"keyword": "Frontend developer", "location": "Pune"},
                {"keyword": "Senior Frontend developer", "location": "Pune"},
                {"keyword": "Angular developer", "location": "Pune"},
                {"keyword": "Senior Angular developer", "location": "Pune"},
                {"keyword": "Full Stack developer", "location": "Pune"},
                {"keyword": "Senior Full Stack developer", "location": "Pune"},
            ]

            for query in queries:
                print(f"{Fore.CYAN}Searching jobs for: {query['keyword']} in {query['location']}...{Style.RESET_ALL}")
                
                for page in range(1, 5):
                    print(f"Fetching page {page}...")
                    try:
                        raw_jobs = await jc.search_jobs(
                            keyword=query["keyword"], 
                            location=query["location"], 
                            experience=4, 
                            job_age=2,
                            page=page
                        )
                    except Exception as e:
                        if "400" in str(e) and "Requested page number doesn't exists" in str(e):
                            print(f"{Fore.YELLOW}  No more pages available for this query.{Style.RESET_ALL}")
                            break
                        else:
                            print(f"{Fore.RED}  Error on page {page}: {e}{Style.RESET_ALL}")
                            break

                    if not raw_jobs:
                        print(f"{Fore.YELLOW}  No more jobs found for this query on page {page}.{Style.RESET_ALL}")
                        break

                    # Random jitter between page fetches
                    await asyncio.sleep(random.uniform(3, 7))

                    # Filter out already applied jobs BEFORE AI to save costs
                    new_jobs = [job for job in raw_jobs if not logger.is_applied(job.job_id) and str(job.job_id) not in pending_jobs]

                    if not new_jobs:
                        print(f"{Fore.YELLOW}  All jobs on page {page} already applied/pending. Skipping AI filter.{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}Filtering {len(new_jobs)} new jobs through AI Pipeline...{Style.RESET_ALL}")
                        filter_pipeline = JobFilterPipeline2(openai_api_key=os.getenv("OPENAI_API_KEY"))
                        jobs = filter_pipeline.run(new_jobs)

                        if not jobs:
                            print(f"{Fore.YELLOW}  No jobs passed the filter.{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.GREEN}Found {len(jobs)} high-quality jobs{Style.RESET_ALL}")

                            for job in jobs:
                                pending_jobs[str(job.job_id)] = job
                                
                                if bot and chat_id and chat_id != "your_telegram_chat_id_here":
                                    ai_score = getattr(job, "match_score", getattr(job, "ai_score", "N/A"))
                                    ai_reason = getattr(job, "reasoning", getattr(job, "ai_reason", "N/A"))
                                    
                                    # Format salary safely
                                    salary_str = job.salary
                                    if isinstance(salary_str, dict):
                                        if salary_str.get("hideSalary"):
                                            salary_str = "Not disclosed"
                                        else:
                                            min_s = salary_str.get("minimumSalary", "")
                                            max_s = salary_str.get("maximumSalary", "")
                                            curr = salary_str.get("currency", "INR")
                                            if min_s or max_s:
                                                salary_str = f"{min_s} - {max_s} {curr}"
                                            else:
                                                salary_str = "Not disclosed"
                                    elif not salary_str:
                                        salary_str = "Not disclosed"

                                    # Format description safely
                                    desc_str = job.description or "No description available."
                                    desc_str = re.sub(r'<[^>]+>', '', desc_str) # strip basic html
                                    if len(desc_str) > 250:
                                        desc_str = desc_str[:247] + "..."
                                        
                                    text = (
                                        f"🏢 *{job.company}*\n"
                                        f"📌 *{job.title}*\n"
                                        f"💰 {salary_str}\n"
                                        f"⏳ {job.experience}\n"
                                        f"📍 {job.location}\n"
                                        f"📅 *Posted:* {job.posted_date}\n"
                                        f"🔗 [View on Naukri]({job.apply_link})\n"
                                        f"🤖 *AI Score:* {ai_score}/100\n"
                                        f"📝 *Reason:* {ai_reason}\n"
                                        f"\n📄 *Description:*\n_{desc_str}_\n"
                                    )
                                    keyboard = [
                                        [
                                            InlineKeyboardButton("✅ Apply", callback_data=f"apply:{job.job_id}"),
                                            InlineKeyboardButton("❌ Skip", callback_data=f"skip:{job.job_id}")
                                        ]
                                    ]
                                    reply_markup = InlineKeyboardMarkup(keyboard)
                                    await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown', reply_markup=reply_markup)
                                    print(f"{Fore.GREEN}   Sent Telegram notification for job {job.job_id}{Style.RESET_ALL}")
                                else:
                                    print(f"{Fore.YELLOW}   Telegram not configured. Job pending: {job.title}{Style.RESET_ALL}")

                    # Increased delay between page fetches to avoid rate limits
                    await asyncio.sleep(random.uniform(5, 10))

        except Exception as e:
            print(f"{Fore.RED}Error in job search loop: {e}{Style.RESET_ALL}")
            
        print(f"{Fore.YELLOW}Sleeping for 10 minutes...{Style.RESET_ALL}")
        await asyncio.sleep(600)

async def main_async():
    global jc, logger
    
    username = os.getenv("NAUKRI_USERNAME")
    password = os.getenv("NAUKRI_PASSWORD")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not telegram_token or telegram_token == "your_telegram_bot_token_here":
        print(f"{Fore.RED}Warning: TELEGRAM_BOT_TOKEN is missing or not set in .env{Style.RESET_ALL}")

    client = NaukriLoginClient(username, password)
    await client.login()

    ai = AIHandler()
    ai.extract_profile()

    jc = NaukriJobClient(client, ai_handler=ai)
    logger = JobLogger()

    app = None
    if telegram_token and telegram_token != "your_telegram_bot_token_here":
        app = ApplicationBuilder().token(telegram_token).connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0).build()
        app.add_handler(CallbackQueryHandler(button_callback))
        await app.initialize()
        await app.start()
        await app.updater.start_polling()

    # Run the search loop concurrently
    search_task = asyncio.create_task(job_search_loop(app))
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        search_task.cancel()
        if app:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Script stopped by user.{Style.RESET_ALL}")