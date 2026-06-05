import os
import sys
import json
import subprocess
import asyncio
import logging
import re
import atexit
from datetime import datetime
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Load env variables
load_dotenv()

# Set up logging and write to both console and controller.log
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/controller.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Intercept sys.stdout and sys.stderr to capture everything printed (e.g. by main.py) in controller.log
class LoggerWriter:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8", errors="ignore")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = LoggerWriter("logs/controller.log")
sys.stderr = LoggerWriter("logs/controller.log")

# Configuration
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
STATE_FILE = "services_state.json"

# State dicts for running processes and tasks
active_processes = {}  # name -> (subprocess.Popen, log_file_handle)
active_tasks = {}      # name -> asyncio.Task

# Helper: Safe edit message text to avoid BadRequest if content hasn't changed
async def edit_message_safe(query, text, reply_markup=None, parse_mode='HTML'):
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise e
        else:
            logger.debug("Message not modified; skipping edit.")

# Helper: Strip ANSI escape sequences (for sending clean logs to Telegram)
def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# Helper: Get last N lines of a file
def tail_file(file_path, num_lines=15):
    if not os.path.exists(file_path):
        return "No logs available yet."
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return "".join(lines[-num_lines:])
    except Exception as e:
        return f"Error reading logs: {e}"

# State persistence helpers
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "email_automation": "stopped",
        "company_finding": "stopped",
        "job_finding": "stopped",
        "profile_update": "stopped"
    }

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {e}")

# Authorization decorator
def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id if update.effective_chat else None
        if CHAT_ID and chat_id != CHAT_ID:
            logger.warning(f"Unauthorized command access attempt from Chat ID: {chat_id}")
            return
        return await func(update, context)
    return wrapper

# Subprocess Management
def start_subprocess(name, cmd, log_filename):
    try:
        log_file = open(f"logs/{log_filename}", "a", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        active_processes[name] = (proc, log_file)
        logger.info(f"Started subprocess {name} with PID {proc.pid}")
        return proc.pid
    except Exception as e:
        logger.error(f"Failed to start subprocess {name}: {e}")
        return None

def stop_subprocess(name):
    if name in active_processes:
        proc, log_file = active_processes[name]
        logger.info(f"Stopping subprocess {name} (PID: {proc.pid})...")
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Subprocess {name} did not exit cleanly. Force killing...")
                proc.kill()
                proc.wait()
        except Exception as e:
            logger.error(f"Error stopping subprocess {name}: {e}")
        finally:
            try:
                log_file.close()
            except:
                pass
            if name in active_processes:
                del active_processes[name]
        return True
    return False

# Naukri Job Finder task management
async def start_job_finding_task(application):
    import main
    from src.client.naukri_client import NaukriLoginClient
    from src.client.job_client import NaukriJobClient
    from src.utils.ai_handler import AIHandler
    from src.utils.job_logger import JobLogger

    username = os.getenv("NAUKRI_USERNAME")
    password = os.getenv("NAUKRI_PASSWORD")

    logger.info("Logging into Naukri client for Job Finder...")
    client = NaukriLoginClient(username, password)
    await client.login()

    ai = AIHandler()
    ai.extract_profile()

    main.jc = NaukriJobClient(client, ai_handler=ai)
    main.logger = JobLogger()
    
    # Run the existing main.py job search loop inside our current event loop
    task = asyncio.create_task(main.job_search_loop(application))
    active_tasks["job_finding"] = task
    logger.info("Naukri Job Finder asyncio task launched.")

def stop_job_finding_task():
    if "job_finding" in active_tasks:
        task = active_tasks["job_finding"]
        task.cancel()
        del active_tasks["job_finding"]
        logger.info("Cancelled Naukri Job Finder asyncio task.")
        
        # Shut down Playwright browser to release locks and resources
        import main
        if main.jc and main.jc._client:
            logger.info("Closing Naukri client browser context...")
            asyncio.create_task(main.jc._client.close())
        return True
    return False

# UI Text and Keyboard generators
def get_status_text(state):
    email_status = "🟢 RUNNING" if state.get("email_automation") == "running" else "🛑 STOPPED"
    company_status = "🟢 RUNNING" if state.get("company_finding") == "running" else "🛑 STOPPED"
    job_status = "🟢 RUNNING" if state.get("job_finding") == "running" else "🛑 STOPPED"
    profile_status = "🟢 RUNNING" if state.get("profile_update") == "running" else "🛑 STOPPED"
    
    text = (
        "🤖 <b>NopeRi Automation Command Deck</b>\n\n"
        f"📧 <b>Email Automation:</b> {email_status}\n"
        f"🏢 <b>Company Email Finding:</b> {company_status}\n"
        f"🔍 <b>Naukri Job Finder:</b> {job_status}\n"
        f"👤 <b>Naukri Profile Update:</b> {profile_status}\n\n"
        "<i>Select an action below to toggle services:</i>"
    )
    return text

def get_status_keyboard(state):
    keyboard = []
    
    # Email Automation row
    email_label = "🛑 Stop Email Automation" if state.get("email_automation") == "running" else "📧 Start Email Automation"
    keyboard.append([InlineKeyboardButton(email_label, callback_data="toggle_emails")])
    
    # Company Finding row
    company_label = "🛑 Stop Company Finding" if state.get("company_finding") == "running" else "🏢 Start Company Finding"
    keyboard.append([InlineKeyboardButton(company_label, callback_data="toggle_company")])
    
    # Job Finding row
    job_label = "🛑 Stop Job Finder" if state.get("job_finding") == "running" else "🔍 Start Job Finder"
    keyboard.append([InlineKeyboardButton(job_label, callback_data="toggle_jobs")])
    
    # Profile Update row
    profile_label = "🛑 Stop Profile Updater" if state.get("profile_update") == "running" else "👤 Start Profile Updater"
    keyboard.append([InlineKeyboardButton(profile_label, callback_data="toggle_profile")])
    
    # Utility row
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_status"),
        InlineKeyboardButton("📊 System Stats", callback_data="show_stats")
    ])
    
    return InlineKeyboardMarkup(keyboard)

# Telegram Command Handlers
@authorized
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    await update.message.reply_text(
        text=get_status_text(state),
        reply_markup=get_status_keyboard(state),
        parse_mode='HTML'
    )

@authorized
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    
    # Get database stats
    from src.utils.dbhandler import OutreachDB
    db = OutreachDB()
    stats = db.get_pipeline_stats()
    
    email_status = "🟢 RUNNING" if state.get("email_automation") == "running" else "🛑 STOPPED"
    company_status = "🟢 RUNNING" if state.get("company_finding") == "running" else "🛑 STOPPED"
    job_status = "🟢 RUNNING" if state.get("job_finding") == "running" else "🛑 STOPPED"
    profile_status = "🟢 RUNNING" if state.get("profile_update") == "running" else "🛑 STOPPED"
    
    text = (
        "🤖 <b>NopeRi Automation Command Deck</b>\n\n"
        "<b>Service Statuses:</b>\n"
        f"📧 <b>Email Automation:</b> {email_status}\n"
        f"🏢 <b>Company Email Finding:</b> {company_status}\n"
        f"🔍 <b>Naukri Job Finder:</b> {job_status}\n"
        f"👤 <b>Naukri Profile Update:</b> {profile_status}\n\n"
        "<b>Outreach Database Statistics:</b>\n"
        f"• Total Discovered: {stats.get('discovered', 0)}\n"
        f"• With Website: {stats.get('website_found', 0)}\n"
        f"• With Emails: {stats.get('email_found', 0)}\n"
        f"• Drafted Outreach: {stats.get('drafted', 0)}\n"
        f"• Emails Sent: {stats.get('sent', 0)}\n"
        f"• Emails Bounced: {stats.get('bounced', 0)}\n"
    )
    
    await update.message.reply_text(text=text, reply_markup=get_status_keyboard(state), parse_mode='HTML')

@authorized
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = context.args[0].lower() if context.args else "controller"
    
    log_files = {
        "emails": "logs/email_automation.log",
        "companies": "logs/company_finding.log",
        "profile": "logs/profile_update.log",
        "controller": "logs/controller.log"
    }
    
    if service not in log_files:
        await update.message.reply_text(
            "❌ Invalid service. Choose from: <code>emails</code>, <code>companies</code>, <code>profile</code>, <code>controller</code>.\n"
            "Example: <code>/logs emails</code>",
            parse_mode='HTML'
        )
        return
        
    file_path = log_files[service]
    logs = tail_file(file_path, num_lines=20)
    clean_logs = strip_ansi_codes(logs)
    
    await update.message.reply_text(
        f"📋 <b>Recent Logs for {service.capitalize()}:</b>\n\n"
        f"<code>{clean_logs}</code>",
        parse_mode='HTML'
    )

@authorized
async def find_companies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/find_companies Location | Radius</code>\n"
            "Example: <code>/find_companies Baner, Pune | 10</code>",
            parse_mode='HTML'
        )
        return
        
    text = " ".join(context.args)
    location = ""
    radius = 10
    if "|" in text:
        parts = text.split("|", 1)
        location = parts[0].strip()
        try:
            radius = int(parts[1].strip())
        except ValueError:
            radius = 10
    else:
        location = text
        
    state = load_state()
    if state.get("company_finding") == "running":
        await update.message.reply_text("❌ Company finding is already running. Please stop or wait for it to complete.")
        return
        
    cmd = [
        sys.executable,
        "find_companies.py",
        "--location", location,
        "--radius", str(radius),
        "--mode", "production"
    ]
    pid = start_subprocess("company_finding", cmd, "company_finding.log")
    if pid:
        state["company_finding"] = "running"
        save_state(state)
        await update.message.reply_text(
            f"🚀 Started Company Email Finding for <b>{location}</b> ({radius}km) (PID: {pid})!",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Failed to start Company Email Finding. Check logs for details.")

@authorized
async def stop_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    
    stop_subprocess("email_automation")
    state["email_automation"] = "stopped"
    
    stop_subprocess("company_finding")
    state["company_finding"] = "stopped"
    
    stop_subprocess("profile_update")
    state["profile_update"] = "stopped"
    
    stop_job_finding_task()
    state["job_finding"] = "stopped"
    
    save_state(state)
    await update.message.reply_text("🛑 Stopped all active services.")

@authorized
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if we are waiting for company search query
    if context.user_data.get('awaiting_company_input'):
        text = update.message.text.strip()
        
        if text.lower() in ("/cancel", "cancel"):
            context.user_data['awaiting_company_input'] = False
            await update.message.reply_text("❌ Cancelled company search.")
            state = load_state()
            await update.message.reply_text(
                text=get_status_text(state),
                reply_markup=get_status_keyboard(state),
                parse_mode='HTML'
            )
            return
            
        location = ""
        radius = 10
        if "|" in text:
            parts = text.split("|", 1)
            location = parts[0].strip()
            try:
                radius = int(parts[1].strip())
            except ValueError:
                radius = 10
        else:
            location = text
            
        if not location:
            await update.message.reply_text("❌ Location cannot be empty. Reply with Location | Radius, or type cancel.")
            return
            
        context.user_data['awaiting_company_input'] = False
        state = load_state()
        
        cmd = [
            sys.executable,
            "find_companies.py",
            "--location", location,
            "--radius", str(radius),
            "--mode", "production"
        ]
        pid = start_subprocess("company_finding", cmd, "company_finding.log")
        if pid:
            state["company_finding"] = "running"
            save_state(state)
            await update.message.reply_text(
                f"🚀 Started Company Email Finding for <b>{location}</b> ({radius}km) (PID: {pid})!\n"
                f"You will get real-time lead updates on Telegram.",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text("❌ Failed to start Company Email Finding. Check logs.")
            
        state = load_state()
        await update.message.reply_text(
            text=get_status_text(state),
            reply_markup=get_status_keyboard(state),
            parse_mode='HTML'
        )

# Callback Query Handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    # Authorize
    if CHAT_ID and update.effective_chat.id != CHAT_ID:
        await query.answer("Unauthorized access", show_alert=True)
        return
        
    # Delegate job apply/skip clicks directly to main.py
    if data.startswith("apply:") or data.startswith("skip:"):
        import main
        # Ensure main.jc and main.logger are loaded
        if not main.jc or not main.logger:
            await query.answer("Job Finder is currently offline. Start it first.", show_alert=True)
            return
        await main.button_callback(update, context)
        return

    # Handle service toggle button clicks
    state = load_state()
    
    if data == "toggle_emails":
        if state.get("email_automation") == "running":
            stop_subprocess("email_automation")
            state["email_automation"] = "stopped"
            await query.answer("Email Automation stopped.")
        else:
            cmd = [sys.executable, "send_emails.py", "--loop", "--interval", "15"]
            pid = start_subprocess("email_automation", cmd, "email_automation.log")
            if pid:
                state["email_automation"] = "running"
                await query.answer(f"Email Automation started (PID: {pid}).")
            else:
                await query.answer("Failed to start Email Automation.", show_alert=True)
        save_state(state)
        await edit_message_safe(query, text=get_status_text(state), reply_markup=get_status_keyboard(state), parse_mode='HTML')
        
    elif data == "toggle_profile":
        if state.get("profile_update") == "running":
            stop_subprocess("profile_update")
            state["profile_update"] = "stopped"
            await query.answer("Profile Updater stopped.")
        else:
            cmd = [sys.executable, "updateDaily.py"]
            pid = start_subprocess("profile_update", cmd, "profile_update.log")
            if pid:
                state["profile_update"] = "running"
                await query.answer(f"Profile Updater started (PID: {pid}).")
            else:
                await query.answer("Failed to start Profile Updater.", show_alert=True)
        save_state(state)
        await edit_message_safe(query, text=get_status_text(state), reply_markup=get_status_keyboard(state), parse_mode='HTML')
        
    elif data == "toggle_jobs":
        if state.get("job_finding") == "running":
            stop_job_finding_task()
            state["job_finding"] = "stopped"
            await query.answer("Naukri Job Finder stopped.")
            save_state(state)
            await edit_message_safe(query, text=get_status_text(state), reply_markup=get_status_keyboard(state), parse_mode='HTML')
        else:
            await query.answer("Starting Naukri Job Finder...")
            await edit_message_safe(
                query,
                text="🔄 Logging into Naukri and starting Job Finder task... Please wait.",
                parse_mode='HTML'
            )
            try:
                await start_job_finding_task(context.application)
                state["job_finding"] = "running"
                save_state(state)
                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text="✅ Naukri Job Finder is now running in the background!"
                )
            except Exception as e:
                logger.error(f"Error starting job finder: {e}")
                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"❌ Failed to start Naukri Job Finder:\n<code>{str(e)}</code>",
                    parse_mode='HTML'
                )
            state = load_state()
            try:
                await context.bot.send_message(
                    chat_id=CHAT_ID,
                    text=get_status_text(state),
                    reply_markup=get_status_keyboard(state),
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error returning status deck: {e}")

    elif data == "toggle_company":
        if state.get("company_finding") == "running":
            stop_subprocess("company_finding")
            state["company_finding"] = "stopped"
            save_state(state)
            await query.answer("Company Finder stopped.")
            await edit_message_safe(query, text=get_status_text(state), reply_markup=get_status_keyboard(state), parse_mode='HTML')
        else:
            context.user_data['awaiting_company_input'] = True
            await query.answer()
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=(
                    "🏢 <b>Find Company Emails</b>\n\n"
                    "Please reply to this message (or just type a message) with the location and radius in this format:\n"
                    "<code>Location | Radius</code> (e.g. <code>Baner, Pune | 10</code>)\n\n"
                    "Or send <code>/cancel</code> to abort."
                ),
                parse_mode='HTML'
            )
            
    elif data == "refresh_status":
        await query.answer("Status refreshed.")
        await edit_message_safe(query, text=get_status_text(state), reply_markup=get_status_keyboard(state), parse_mode='HTML')
        
    elif data == "show_stats":
        from src.utils.dbhandler import OutreachDB
        db = OutreachDB()
        stats = db.get_pipeline_stats()
        
        text = (
            "📊 <b>Outreach Database Statistics</b>\n\n"
            f"• Total Discovered: {stats.get('discovered', 0)}\n"
            f"• With Website: {stats.get('website_found', 0)}\n"
            f"• With Emails: {stats.get('email_found', 0)}\n"
            f"• Drafted Outreach: {stats.get('drafted', 0)}\n"
            f"• Emails Sent: {stats.get('sent', 0)}\n"
            f"• Emails Bounced: {stats.get('bounced', 0)}\n"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Controller", callback_data="refresh_status")]]
        await query.answer("Stats fetched.")
        await edit_message_safe(query, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# Poller to check if background processes have completed/exited
async def monitor_subprocesses(bot):
    while True:
        try:
            for name in list(active_processes.keys()):
                proc, log_file = active_processes[name]
                exit_code = proc.poll()
                if exit_code is not None:
                    logger.info(f"Subprocess '{name}' exited with code {exit_code}")
                    try:
                        log_file.close()
                    except:
                        pass
                    if name in active_processes:
                        del active_processes[name]
                    
                    state = load_state()
                    state[name] = "stopped"
                    save_state(state)
                    
                    friendly_names = {
                        "email_automation": "📧 Email Automation",
                        "company_finding": "🏢 Company Email Finding",
                        "profile_update": "👤 Naukri Profile Daily Update"
                    }
                    friendly_name = friendly_names.get(name, name)
                    
                    service_name = name
                    if name == "company_finding":
                        service_name = "companies"
                    elif name == "email_automation":
                        service_name = "emails"
                    elif name == "profile_update":
                        service_name = "profile"
                    
                    if exit_code == 0:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"✅ <b>{friendly_name}</b> has completed successfully.",
                            parse_mode='HTML'
                        )
                    else:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"⚠️ <b>{friendly_name}</b> stopped unexpectedly with exit code <b>{exit_code}</b>. View logs with <code>/logs {service_name}</code>.",
                            parse_mode='HTML'
                        )
        except Exception as e:
            logger.error(f"Error in monitor_subprocesses loop: {e}")
        await asyncio.sleep(5)

# Boot/Resume logic
async def resume_active_services(application):
    state = load_state()
    
    # Treat company finding as stopped on startup since it's a one-shot process
    if state.get("company_finding") == "running":
        state["company_finding"] = "stopped"
        save_state(state)

    logger.info("Resuming previously active services...")

    # Resume Email Automation
    if state.get("email_automation") == "running":
        cmd = [sys.executable, "send_emails.py", "--loop", "--interval", "15"]
        pid = start_subprocess("email_automation", cmd, "email_automation.log")
        if pid:
            logger.info(f"Resumed Email Automation (PID: {pid})")
        else:
            state["email_automation"] = "stopped"
            save_state(state)

    # Resume Profile Updater
    if state.get("profile_update") == "running":
        cmd = [sys.executable, "updateDaily.py"]
        pid = start_subprocess("profile_update", cmd, "profile_update.log")
        if pid:
            logger.info(f"Resumed Profile Updater (PID: {pid})")
        else:
            state["profile_update"] = "stopped"
            save_state(state)

    # Resume Job Finder
    if state.get("job_finding") == "running":
        try:
            await start_job_finding_task(application)
            logger.info("Resumed Naukri Job Finder task.")
        except Exception as e:
            logger.error(f"Failed to resume Naukri Job Finder: {e}")
            state["job_finding"] = "stopped"
            save_state(state)
            
    # Send online message to user
    try:
        await application.bot.send_message(
            chat_id=CHAT_ID,
            text=(
                "🖥️ <b>NopeRi Controller Bot Online!</b>\n\n"
                "All services that were active when last closed have been successfully resumed.\n"
                "Use /start or /status to view the command deck."
            ),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Could not send boot message: {e}")

# Shutdown Cleanup
def cleanup():
    logger.info("Running controller shutdown cleanup...")
    for name in list(active_processes.keys()):
        stop_subprocess(name)
    stop_job_finding_task()
    logger.info("Cleanup complete.")

# Main Application Entry Point
def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        logger.error("TELEGRAM_BOT_TOKEN is missing or not set in .env! Exiting.")
        sys.exit(1)
        
    if not CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID is missing or not set in .env! Exiting.")
        sys.exit(1)

    logger.info("Starting NopeRi Controller Hub Telegram bot...")

    # Create application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("find_companies", find_companies_command))
    application.add_handler(CommandHandler("stop_all", stop_all_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register exit hooks
    atexit.register(cleanup)

    # Fetch event loop to run startup hooks and pollers
    loop = asyncio.get_event_loop()
    
    # Run resume logic and subprocess poller
    loop.create_task(resume_active_services(application))
    loop.create_task(monitor_subprocesses(application.bot))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    main()
