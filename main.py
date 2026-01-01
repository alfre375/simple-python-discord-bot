import json
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import random

random_word_list: list[str] = []
with open('random_word_list.txt') as listfile:
    if type(listfile) == str:
        random_word_list = listfile.split('\n')
    else:
        random_word_list = listfile.readlines()
        listfile.close()

data = {}
if not os.path.exists('./data'):
    os.mkdir('./data')
data_files_list = os.listdir('./data')
print(data_files_list)
for item in data_files_list:
    if not item.endswith('.json'):
        continue
    with open('./data/' + item, 'r') as file:
        if type(file) == str:
            data = json.loads(file)
        else:
            data = json.loads(file.read())
            file.close()

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    
    print(f'A message was sent: {message.content}')
    
    if message.content.startswith('$'):
        await msg_command(message)

bot = commands.Bot('ª', intents=intents)
@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User | discord.Member):
    if user.bot:
        return
    
    message = reaction.message
    
    print(f'User {user.id} ({user.display_name}) reacted with {reaction.emoji} to {message.id} (which says {message.content})')
    
    if message.channel.guild.id in data:
        if message.channel.id in data[message.channel.guild.id]:
            if message.id in data[message.channel.guild.id][message.channel.id]:
                if 'reaction-commands' in data[message.channel.guild.id][message.channel.id][message.id]:
                    commands_to_run = data[message.channel.guild.id][message.channel.id][message.id]['reaction-commands']
                    for cmd in commands_to_run:
                        await reaction_cmd(cmd, user, message)

async def msg_command(message: discord.Message):
    msg_text = message.content.removeprefix('$').split(' ')
    mt0 = msg_text[0]
    if mt0 == 'hello':
        await message.reply(f'Hello, <@{message.author.id}>!')
    elif mt0 == 'hug':
        await message.add_reaction('🫂')
    elif mt0 == 'add_reply_command':
        message_id_to_apply = msg_text[1]
        emoji_to_apply = msg_text[2]
        command = msg_text
        command.pop(0)
        command.pop(0)
        command.pop(0)
        message_to_apply = await message.channel.fetch_message(message_id_to_apply)
        await message_to_apply.add_reaction(emoji_to_apply)
        # Add to data
        print(message.channel.guild.id)
        if not message.channel.guild.id in data:
            data[message.channel.guild.id] = {
                message.channel.id: {
                    message.id: {
                        'reaction-commands': {
                            emoji_to_apply: command
                        }
                    }
                }
            }
        elif not message.channel.id in data[message.channel.guild.id]:
            data[message.channel.guild.id][message.channel.id] = {
                message.id: {
                    'reaction-commands': {
                        emoji_to_apply: command
                    }
                }
            }
        elif not message.id in data[message.channel.guild.id][message.channel.id]:
            data[message.channel.guild.id][message.channel.id][message.id] = {
                'reaction-commands': {
                    emoji_to_apply: command
                }
            }
        elif not 'reaction-commands' in data[message.channel.guild.id][message.channel.id][message.id]:
            data[message.channel.guild.id][message.channel.id][message.id]['reaction-commands'] = {
                emoji_to_apply: command
            }
        elif not emoji_to_apply in data[message.channel.guild.id][message.channel.id][message.id]['reaction-commands']:
            data[message.channel.guild.id][message.channel.id][message.id]['reaction-commands'][emoji_to_apply] = [command]
        elif not command in data[message.channel.guild.id][message.channel.id][message.id]['reaction-commands']:
            data[message.channel.guild.id][message.channel.id][message.id]['reaction-commands'][emoji_to_apply].append(command)
        with open(f'./data/{message.channel.guild.id}.json', 'w') as file:
            file.write(json.dumps(data[message.channel.guild.id]))
            file.close()
        await message.reply('Done!')
    else:
        await message.reply(f'Invalid command: {msg_text[0]}')

async def reaction_cmd(cmd: list[str], user: discord.User | discord.Member, message: discord.Message):
    channel = message.channel
    if cmd[0] == 'setname':
        cmd.pop(0)
        newname: str = ' '.join(cmd)
        user.display_name = newname
    elif cmd[0] == 'setrandomname':
        user.display_name = random_name
    else:
        channel.send(f'ERR: Invalid command {cmd[0]}')
        

def random_name() -> str:
    return random_word_list[random.randrange(0,len(random_word_list)-1)] + random_word_list[random.randrange(0,len(random_word_list)-1)] + str(random.randrange(0,999))

client.run(discord_token)