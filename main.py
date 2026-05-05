from src.client.naukri_client import NaukriLoginClient
from src.client.job_client import NaukriJobClient
from src.utils.ai_handler import AIHandler
from src.utils.job_logger import JobLogger
from src.client.jop_classifier import JobFilterPipeline2
from dotenv import load_dotenv
from colorama import Fore, Style, init
import os
import time
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

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
        
        try:
            result = jc.apply_job(job, mandatory_skills=mandatory, optional_skills=optional, source="search")
            job_result = (result.get("jobs") or [{}])[0]
            
            if job_result.get("questionnaire"):
                q_result = jc.handle_ai_questionnaire_and_apply(
                    job, 
                    job_result["questionnaire"], 
                    sid="", 
                    mandatory_skills=mandatory, 
                    optional_skills=optional, 
                    source="search"
                )
                q_success = False
                if q_result.get("status") == "success":
                    q_success = True
                elif "applyStatus" in q_result and str(job.job_id) in q_result.get("applyStatus", {}):
                    q_success = True
                elif (q_result.get("jobs") or [{}])[0].get("applyStatus"):
                    q_success = True

                if q_success:
                    logger.log_apply(job.job_id, job.title, job.company)
                    await query.edit_message_text(text="✅ Applied! (AI solved questionnaire)")
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
        except Exception as e:
            await query.edit_message_text(text=f"❌ Failed: {e}")
            
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
            print("Searching jobs...")    
            raw_jobs = jc.search_jobs(keyword="Angular developer", location="Pune", experience=4, job_age=7)

            if not raw_jobs:
                print(f"{Fore.YELLOW}  No jobs found from search.{Style.RESET_ALL}")
                jobs = []
            else:
                print(f"{Fore.CYAN}Filtering jobs through AI Pipeline...{Style.RESET_ALL}")
                filter_pipeline = JobFilterPipeline2(openai_api_key=os.getenv("OPENAI_API_KEY"))
                jobs = filter_pipeline.run(raw_jobs) if raw_jobs else []

            if not jobs:
                print(f"{Fore.YELLOW}  No jobs passed the filter.{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}Found {len(jobs)} high-quality jobs{Style.RESET_ALL}")

                for job in jobs:
                    if logger.is_applied(job.job_id):
                        print(f"{Fore.BLUE}   [SKIP] Already applied previously.{Style.RESET_ALL}")
                        continue
                    
                    if str(job.job_id) in pending_jobs:
                        continue

                    pending_jobs[str(job.job_id)] = job
                    
                    if bot and chat_id and chat_id != "your_telegram_chat_id_here":
                        # We use getattr to safely get the properties, defaulting to existing properties if ai_* missing
                        ai_score = getattr(job, "match_score", getattr(job, "ai_score", "N/A"))
                        ai_reason = getattr(job, "reasoning", getattr(job, "ai_reason", "N/A"))
                        text = (
                            f"🏢 *{job.company}*\n"
                            f"📌 *{job.title}*\n"
                            f"💰 {job.salary} | ⏳ {job.experience} | 📍 {job.location}\n"
                            f"🤖 *AI Score:* {ai_score}/100\n"
                            f"📝 *Reason:* {ai_reason}\n"
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
    client.login()

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
    # ---------------------------------------------------------------
    # This architecture now uses asyncio to run Telegram bot polling 
    # alongside the job search loop asynchronously.
    # ---------------------------------------------------------------
    asyncio.run(main_async())