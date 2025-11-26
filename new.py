"""
Telegram Referral Bot
A sophisticated referral system bot that automatically approves channel join requests
after users complete their referral requirements.

Author: Your Name
Version: 1.1
"""

import logging
import json
import os
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, ChatJoinRequestHandler, filters
)
from telegram.error import BadRequest, TelegramError

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ReferralBot:
    """Main Referral Bot Class"""
    
    def __init__(self):
        self.config = self.load_config()
        self.user_data_file = "user_data.json"
        
    def load_config(self):
        """Load configuration from environment variables or defaults"""
        return {
            'BOT_TOKEN': os.getenv('BOT_TOKEN', "8423366349:AAGLtC52fynmexw-vq11AhoEe-wWcnq7DEI"),
            'MOVIE_CHANNEL_LINK': os.getenv('MOVIE_CHANNEL_LINK', "https://t.me/+EJZw_EJvlxE5NzNl"),
            'CHANNEL_ID': os.getenv('CHANNEL_ID', "-1003495187212"),
            'REFERRAL_POINTS': int(os.getenv('REFERRAL_POINTS', 3)),
            'REQUIRED_REFERRALS': int(os.getenv('REQUIRED_REFERRALS', 3)),
            'BOT_USERNAME': os.getenv('BOT_USERNAME', "deshi_media_de_bot"),
            'ADMIN_USER_ID': os.getenv('ADMIN_USER_ID', "YOUR_ADMIN_USER_ID_HERE"),
            'USER_RETENTION_DAYS': int(os.getenv('USER_RETENTION_DAYS', 7))
        }

    def load_user_data(self):
        """Load user data from JSON file"""
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading user data: {e}")
                return {}
        return {}

    def save_user_data(self, data):
        """Save user data to JSON file"""
        try:
            with open(self.user_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
            return False

    def get_referral_link(self, user_id):
        """Generate referral link for user"""
        return f"https://t.me/{self.config['BOT_USERNAME']}?start={user_id}"

    async def notify_admin_referral_complete(self, context: ContextTypes.DEFAULT_TYPE, user_info, user_id):
        """
        Notify admin when a user completes referrals
        
        Args:
            context: Bot context
            user_info: User data dictionary
            user_id: Telegram user ID
        """
        try:
            admin_message = f"""
🎯 **NEW REFERRAL COMPLETED!**

👤 **User Details:**
• Name: {user_info.get('first_name', 'N/A')}
• Username: @{user_info.get('username', 'N/A')}
• User ID: `{user_id}`
• Total Referrals: {len(user_info.get('referrals', []))}
• Total Points: {user_info.get('points', 0)}
• Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ **User is now eligible for channel access!**
            """
            
            await context.bot.send_message(
                chat_id=self.config['ADMIN_USER_ID'],
                text=admin_message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Admin notified about user {user_id} completing referrals")
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")

    async def is_user_in_channel(self, user_id, context: ContextTypes.DEFAULT_TYPE):
        """Check if user is already in channel"""
        try:
            member = await context.bot.get_chat_member(self.config['CHANNEL_ID'], user_id)
            return member.status in ['member', 'administrator', 'creator']
        except BadRequest:
            return False
        except Exception as e:
            logger.error(f"Error checking channel membership: {e}")
            return False

    async def approve_channel_request(self, user_id, context: ContextTypes.DEFAULT_TYPE):
        """Approve user's channel join request"""
        try:
            await context.bot.approve_chat_join_request(self.config['CHANNEL_ID'], user_id)
            logger.info(f"Successfully approved user {user_id} for channel")
            return True
        except Exception as e:
            logger.error(f"Error approving user {user_id}: {e}")
            return False

    async def decline_channel_request(self, user_id, context: ContextTypes.DEFAULT_TYPE):
        """Decline user's channel join request"""
        try:
            await context.bot.decline_chat_join_request(self.config['CHANNEL_ID'], user_id)
            logger.info(f"Declined join request for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error declining user {user_id}: {e}")
            return False

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command
        Processes referrals and initializes user data
        """
        user = update.effective_user
        user_id = str(user.id)
        user_data = self.load_user_data()
        
        # Check if it's a referral
        if context.args:
            referrer_id = context.args[0]
            if referrer_id != user_id and referrer_id in user_data:
                if 'referrals' not in user_data[referrer_id]:
                    user_data[referrer_id]['referrals'] = []
                
                if user_id not in user_data[referrer_id]['referrals']:
                    # Add referral to list
                    user_data[referrer_id]['referrals'].append(user_id)
                    
                    # Add points only for first 3 referrals
                    current_referrals = len(user_data[referrer_id]['referrals'])
                    if current_referrals <= self.config['REQUIRED_REFERRALS']:
                        user_data[referrer_id]['points'] = user_data[referrer_id].get('points', 0) + self.config['REFERRAL_POINTS']
                    
                    self.save_user_data(user_data)
                    
                    # Send points notification for each referral (1st, 2nd, 3rd)
                    updated_user_info = user_data[referrer_id]
                    referrals_count = len(updated_user_info['referrals'])
                    
                    try:
                        points_message = f"""
🎉 **+{self.config['REFERRAL_POINTS']} Points Received!**

📊 **Your Progress:**
• Points: {updated_user_info['points']}
• Referrals: {referrals_count}/{self.config['REQUIRED_REFERRALS']}

{"✅ **Target Completed! You can now join the channel!**" if referrals_count >= self.config['REQUIRED_REFERRALS'] else "Keep sharing your link! 🚀"}
"""
                        await context.bot.send_message(
                            chat_id=int(referrer_id),
                            text=points_message,
                            parse_mode='Markdown'
                        )
                        
                        # ✅ CHANNEL LINK TABHI BHEJO JAB 3 REFERRALS COMPLETE HO
                        if referrals_count >= self.config['REQUIRED_REFERRALS']:
                            channel_message = f"""
🎉 **Congratulations! You've completed {self.config['REQUIRED_REFERRALS']} referrals!**

📺 **Now you can join our channel:**
{self.config['MOVIE_CHANNEL_LINK']}

✅ **Send join request and you'll be auto-approved!**
"""
                            await context.bot.send_message(
                                chat_id=int(referrer_id),
                                text=channel_message,
                                parse_mode='Markdown'
                            )
                            
                    except Exception as e:
                        logger.error(f"Error notifying referrer: {e}")
                    
                    # Notify admin when user completes referrals
                    if referrals_count >= self.config['REQUIRED_REFERRALS']:
                        try:
                            await self.notify_admin_referral_complete(context, updated_user_info, referrer_id)
                        except Exception as e:
                            logger.error(f"Error notifying admin: {e}")
        
        # Initialize user data if not exists
        if user_id not in user_data:
            user_data[user_id] = {
                'points': 0,
                'referrals': [],
                'has_received_link': False,
                'is_approved': False,
                'username': user.username,
                'first_name': user.first_name,
                'registered_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
        else:
            # Update last activity for existing user
            user_data[user_id]['last_activity'] = datetime.now().isoformat()
        
        self.save_user_data(user_data)
        
        user_info = user_data[user_id]
        referral_link = self.get_referral_link(user_id)
        
        # ✅ CHANNEL LINK REMOVE KAR DIYA START MESSAGE SE
        welcome_text = f"""
🤖 **Welcome to Referral Bot!** {user.first_name}

📊 **Your Points:** {user_info['points']}
👥 **Your Referrals:** {len(user_info['referrals'])}/{self.config['REQUIRED_REFERRALS']}

📨 **Your Referral Link:**
`{referral_link}`

**📋 Rules:**
1. Share your referral link with {self.config['REQUIRED_REFERRALS']} people
2. Get +{self.config['REFERRAL_POINTS']} points for each referral
3. Complete {self.config['REQUIRED_REFERRALS']} referrals for channel access
4. Send join request to get auto-approved

**🎯 Target: Complete {self.config['REQUIRED_REFERRALS']} Referrals!**
"""
        
        # ✅ CHANNEL BUTTON REMOVE KAR DIYA
        keyboard = [
            [InlineKeyboardButton("📱 Share Referral Link", 
                                 url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and get rewards!")],
            [InlineKeyboardButton("📊 Check My Status", callback_data="status")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_chat_join_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Auto handle channel join requests
        Approves users who have completed referral requirements
        """
        join_request = update.chat_join_request
        user_id = str(join_request.from_user.id)
        chat_id = join_request.chat.id
        
        logger.info(f"Join request received from user {user_id} for chat {chat_id}")
        
        user_data = self.load_user_data()
        
        # Check if user is registered in bot and has completed referrals
        if user_id in user_data:
            user_info = user_data[user_id]
            
            if len(user_info.get('referrals', [])) >= self.config['REQUIRED_REFERRALS']:
                # Auto-approve the request
                try:
                    await self.approve_channel_request(int(user_id), context)
                    user_data[user_id]['is_approved'] = True
                    user_data[user_id]['has_received_link'] = True
                    user_data[user_id]['approved_at'] = datetime.now().isoformat()
                    self.save_user_data(user_data)
                    
                    # ✅ USER KO KOI MESSAGE NA BHEJO - COMPLETELY SILENT
                    logger.info(f"Auto-approved user {user_id} for channel {chat_id} (silent)")
                    
                except Exception as e:
                    logger.error(f"Error approving user {user_id}: {e}")
                    
            else:
                # User doesn't have enough referrals - decline
                try:
                    await self.decline_channel_request(int(user_id), context)
                    
                    # ✅ USER KO KOI MESSAGE NA BHEJO - COMPLETELY SILENT
                    logger.info(f"Declined join request for user {user_id} (silent)")
                        
                except Exception as e:
                    logger.error(f"Error declining user {user_id}: {e}")
                    
        else:
            # User not registered in bot - decline
            try:
                await self.decline_channel_request(int(user_id), context)
                
                # ✅ USER KO KOI MESSAGE NA BHEJO - COMPLETELY SILENT
                logger.info(f"Declined unregistered user {user_id} (silent)")
                    
            except Exception as e:
                logger.error(f"Error declining unregistered user {user_id}: {e}")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user status with current progress"""
        query = update.callback_query
        if query:
            await query.answer()
            user_id = str(query.from_user.id)
            message = query.message
        else:
            user_id = str(update.effective_user.id)
            message = update.message
        
        user_data = self.load_user_data()
        
        if user_id not in user_data:
            text = "❌ You haven't started the bot yet. Use /start."
            if query:
                await query.edit_message_text(text)
            else:
                await message.reply_text(text)
            return
        
        user_info = user_data[user_id]
        referral_link = self.get_referral_link(user_id)
        
        # Check if user is already in channel
        in_channel = await self.is_user_in_channel(int(user_id), context)
        
        # Add timestamp to make message unique
        timestamp = int(time.time())
        
        status_text = f"""
📊 **Your Status Report:** (Updated)

👤 **User:** {user_info.get('first_name', 'User')}
🏆 **Points:** {user_info['points']}
👥 **Referrals:** {len(user_info['referrals'])}/{self.config['REQUIRED_REFERRALS']}
📺 **Channel Status:** {'✅ Joined' if in_channel else '❌ Not Joined'}
🔗 **Your Link:** `{referral_link}`

"""
        
        keyboard = []
        
        # ✅ CHANNEL LINK TABHI SHOW KARO JAB 3 REFERRALS COMPLETE HO
        if len(user_info['referrals']) >= self.config['REQUIRED_REFERRALS']:
            status_text += "🎉 **Congratulations! You can now join the channel!**\n"
            keyboard.append([InlineKeyboardButton("🎬 Join Channel", 
                                                url=self.config['MOVIE_CHANNEL_LINK'])])
        else:
            status_text += f"🎯 **Target:** {self.config['REQUIRED_REFERRALS'] - len(user_info['referrals'])} more referrals needed!"
            keyboard.append([InlineKeyboardButton("📱 Share Referral Link", 
                                                url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot!")])
        
        keyboard.append([InlineKeyboardButton("🔄 Status Update", callback_data=f"status_{timestamp}")])
        keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            if query:
                await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await message.reply_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')
        except BadRequest as e:
            if "Message is not modified" in str(e):
                if query:
                    await query.answer("✅ Status is already up-to-date!")
                logger.info(f"Message not modified for user {user_id} - normal behavior")
            else:
                raise e

    async def home(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Return to home screen"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(query.from_user.id)
        user_data = self.load_user_data()
        
        if user_id not in user_data:
            await query.edit_message_text("❌ You haven't started the bot yet. Use /start.")
            return
        
        user_info = user_data[user_id]
        referral_link = self.get_referral_link(user_id)
        
        home_text = f"""
🏠 **Referral Bot Home**

📊 **Your Points:** {user_info['points']}
👥 **Your Referrals:** {len(user_info['referrals'])}/{self.config['REQUIRED_REFERRALS']}

📨 **Your Referral Link:**
`{referral_link}`

**What to do?**
1. Share referral link 👥
2. Complete {self.config['REQUIRED_REFERRALS']} referrals ✅
3. Send channel join request 📺
4. Get auto-approved! 🎉
"""
        
        keyboard = [
            [InlineKeyboardButton("📱 Share Referral Link", 
                                 url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot!")],
            [InlineKeyboardButton("📊 My Status", callback_data="status")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ]
        
        # ✅ CHANNEL BUTTON TABHI ADD KARO JAB 3 REFERRALS COMPLETE HO
        if len(user_info['referrals']) >= self.config['REQUIRED_REFERRALS']:
            keyboard.insert(2, [InlineKeyboardButton("🎬 Join Channel", url=self.config['MOVIE_CHANNEL_LINK'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(home_text, reply_markup=reply_markup, parse_mode='Markdown')
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await query.answer("✅ You're already on home page!")
            else:
                raise e

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        query = update.callback_query
        if query:
            await query.answer()
            message = query.message
        else:
            message = update.message
        
        help_text = f"""
❓ **Referral Bot Help Guide**

**🤔 How it works?**
1. **Start Bot** → /start
2. **Get Referral Link** → Your personal link
3. **Share Link** → Send to {self.config['REQUIRED_REFERRALS']} friends
4. **Collect Points** → Each referral = {self.config['REFERRAL_POINTS']} points
5. **Complete Target** → {self.config['REQUIRED_REFERRALS']} referrals
6. **Join Channel** → Send request, get auto-approved!

**📋 Commands:**
/start - Start bot and get referral link
/status - Check your current status
/help - This help message

**🎯 Conditions:**
- {self.config['REQUIRED_REFERRALS']} Referrals required for channel access
- Only registered bot users can be approved
- Auto-approval system for eligible users
"""
        
        keyboard = [
            [InlineKeyboardButton("🏠 Home", callback_data="home")],
            [InlineKeyboardButton("📊 My Status", callback_data="status")],
            [InlineKeyboardButton("🚀 Start Bot", url=f"https://t.me/{self.config['BOT_USERNAME']}?start=start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            if query:
                await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
        except BadRequest as e:
            if "Message is not modified" in str(e):
                if query:
                    await query.answer("✅ Help message is already displayed!")
            else:
                raise e

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin statistics"""
        user_id = str(update.effective_user.id)
        
        if user_id != self.config['ADMIN_USER_ID']:
            await update.message.reply_text("❌ This command is for administrators only.")
            return
        
        user_data = self.load_user_data()
        total_users = len(user_data)
        completed_users = sum(1 for user in user_data.values() if len(user.get('referrals', [])) >= self.config['REQUIRED_REFERRALS'])
        pending_users = total_users - completed_users
        
        # Get recent completed users
        recent_completed = []
        for uid, info in user_data.items():
            if len(info.get('referrals', [])) >= self.config['REQUIRED_REFERRALS']:
                recent_completed.append({
                    'name': info.get('first_name', 'Unknown'),
                    'username': info.get('username', 'N/A'),
                    'user_id': uid,
                    'referrals': len(info.get('referrals', [])),
                    'points': info.get('points', 0),
                    'completed_at': info.get('last_activity', 'N/A')
                })
        
        stats_text = f"""
📊 **Admin Statistics**

👥 **Users Overview:**
• Total Users: {total_users}
• Completed Referrals: {completed_users}
• Pending Users: {pending_users}

🎯 **Recent Completed Users:**
"""
        
        if recent_completed:
            for user in recent_completed[-10:]:  # Show last 10 completed users
                stats_text += f"• {user['name']} (@{user['username']}) - ID: `{user['user_id']}` - {user['referrals']} referrals\n"
        else:
            stats_text += "• No users have completed referrals yet."
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    def setup_handlers(self, application):
        """Setup all bot handlers"""
        # Command handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("admin", self.admin_stats))
        
        # ChatJoinRequest handler
        application.add_handler(ChatJoinRequestHandler(self.handle_chat_join_request))
        
        # Callback query handlers
        application.add_handler(CallbackQueryHandler(self.status, pattern="^status"))
        application.add_handler(CallbackQueryHandler(self.home, pattern="home"))
        application.add_handler(CallbackQueryHandler(self.help_command, pattern="help"))

    def run(self):
        """Start the bot"""
        # Create application
        application = Application.builder().token(self.config['BOT_TOKEN']).build()
        
        # Setup handlers
        self.setup_handlers(application)
        
        # Start bot
        print("🤖 Referral Bot started successfully!")
        print(f"📊 Channel ID: {self.config['CHANNEL_ID']}")
        print(f"🎯 Required Referrals: {self.config['REQUIRED_REFERRALS']}")
        print(f"💰 Points per Referral: {self.config['REFERRAL_POINTS']}")
        print(f"👑 Admin User ID: {self.config['ADMIN_USER_ID']}")
        print("🚀 Waiting for messages and join requests...")
        
        # ***************** YAHAN BADLAV KIYA HAI *******************
        application.run_in_thread()  # Bot ko thread mein chalao
        while True: 
            time.sleep(100)  # Process ko chalu rakho
        # ************************************************************

def main():
    """Main function to start the bot"""
    bot = ReferralBot()
    bot.run()

if __name__ == '__main__':
    main()
