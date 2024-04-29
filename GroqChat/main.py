import os
import re
import json

import discord
from discord.ext import commands
from dotenv import load_dotenv
from groq import Groq

message_history = {}

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
MAX_HISTORY = int(os.getenv("MAX_HISTORY"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))


# --------------------------------------------- Persistent Memory ---------------------------------------------
def load_memory():
    try:
        with open('GroqMemory.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Memory Not Found")
        return {}


def save_memory(memory):
    with open('GroqMemory.json', 'w') as f:
        json.dump(memory, f, indent=4)


# --------------------------------------------- Groq Configuration -------------------------------------------------
client = Groq(api_key=GROQ_API_KEY)

# --------------------------------------------- Discord Code -------------------------------------------------
# Initialize Discord bot
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())


@bot.event
async def on_ready():
    print("----------------------------------------")
    print(f'Groq Bot Logged in as {bot.user}')
    print("----------------------------------------")
    channel = bot.get_channel(CHANNEL_ID)
    global message_history
    try:
        message_history = load_memory()  # Load the memory from the JSON file
    except:
        print("Unable to load history")


# On Message Function
@bot.event
async def on_message(message):
    print("Message received:")
    # Ignore messages sent by the bot
    if message.author == bot.user or message.mention_everyone:
        return
    # Check if the bot is mentioned or the message is a DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        # Start Typing to seem like something happened
        cleaned_text = clean_discord_message(message.content)
        async with message.channel.typing():
            # Handle Message Attachments
            if message.attachments:
                attachment = message.attachments[0]
                if attachment.filename.endswith('.txt'):
                    # Read the contents of the file
                    file_contents = await attachment.read()
                    cleaned_text += '\n' + file_contents.decode('utf-8')

            # Do text response
            print("New Message FROM:" + str(message.author.id) + ": " + cleaned_text)

            # Check for Keyword Reset
            if "RESET" in cleaned_text and len(cleaned_text) < 10:
                # End back message
                if message.author.id in message_history:
                    del message_history[message.author.id]
                save_memory(message_history)
                await message.channel.send("Message History Reset for user: " + str(message.author.name))
                return

            await message.add_reaction('💬')

            # Check if history is disabled just send response
            if (MAX_HISTORY == 0):
                response_text = await generate_response_groq(cleaned_text)
                # add AI response to history
                await split_and_send_messages(message, response_text, 1700)
                return

            # Add users question to history
            update_message_history(message.author.id, "user", cleaned_text)
            response_text = await generate_response_groq(get_formatted_message_history(message.author.id))

            # add AI response to history
            update_message_history(message.author.id, "assistant", response_text)
            # Split the Message so discord does not get upset
            await split_and_send_messages(message, response_text, 1700)


# --------------------------------------------- Groq Generation --------------------------------------------------
system_prompt = ""


async def generate_response_groq(message_history):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # Add the conversation history
    for role, content in message_history:
        messages.append({"role": role, "content": content})

    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",  # Keep your existing model choice
        temperature=0.5,
        max_tokens=1024,
    )

    response = chat_completion.choices[0].message.content
    return response


# --------------------------------------------- Message History -------------------------------------------------
def update_message_history(user_id, role, text):
    if user_id not in message_history:
        message_history[user_id] = []
    message_history[user_id].append((role, text))
    if len(message_history[user_id]) > MAX_HISTORY:
        message_history[user_id].pop(0)
    save_memory(message_history)


def get_formatted_message_history(user_id):
    if user_id in message_history:
        return message_history[user_id]
    else:
        return []


# --------------------------------------------- Sending Messages -------------------------------------------------
async def split_and_send_messages(message_system, text, max_length):
    # Split the string into parts
    messages = []
    for i in range(0, len(text), max_length):
        sub_message = text[i:i + max_length]
        messages.append(sub_message)

    # Send each part as a separate message
    for string in messages:
        await message_system.channel.send(string)


def clean_discord_message(input_string):
    # Create a regular expression pattern to match text between < and >
    bracket_pattern = re.compile(r'<[^>]+>')
    # Replace text between brackets with an empty string
    cleaned_content = bracket_pattern.sub('', input_string)
    return cleaned_content


# --------------------------------------------- Run Bot -------------------------------------------------
bot.run(DISCORD_BOT_TOKEN)
