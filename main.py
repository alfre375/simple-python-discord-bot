import json
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import random

debug_mode: bool = False

def debug(*msg: str):
    if debug_mode:
        print(*msg)

random_word_list: list = []
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
debug(data_files_list)
for item in data_files_list:
    if not item.endswith('.json'):
        continue
    with open('./data/' + item, 'r') as file:
        if type(file) == str:
            data[item.removesuffix('.json')] = json.loads(file)
        else:
            data[item.removesuffix('.json')] = json.loads(file.read())
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
    
    debug(f'A message was sent: {message.content}')
    
    if message.content.startswith('$'):
        await msg_command(message)

#bot = commands.Bot('ª', intents=intents)
@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    channel = client.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = payload.member
    
    if user.bot:
        return
    
    debug(f'User {user.id} ({user.display_name}) reacted with {payload.emoji} to {message.id} (which says {message.content})')
    
    debug(f'Data: {json.dumps(data)}')
    if str(message.channel.guild.id) in data.keys():
        debug('Guild has data!')
        if str(message.channel.id) in data[str(message.channel.guild.id)].keys():
            debug('Channel has data!')
            if str(message.id) in data[str(message.channel.guild.id)][str(message.channel.id)].keys():
                debug('Message has data!')
                if 'reaction-commands' in data[str(message.channel.guild.id)][str(message.channel.id)][str(message.id)].keys():
                    debug('Reaction commands list found!')
                    if str(payload.emoji) in data[str(message.channel.guild.id)][str(message.channel.id)][str(message.id)]['reaction-commands'].keys():
                        debug('Emoji is registered with commands')
                        commands_to_run = data[str(message.channel.guild.id)][str(message.channel.id)][str(message.id)]['reaction-commands'][str(payload.emoji)]
                        debug(commands_to_run)
                        for cmd in commands_to_run:
                            debug('cmd: ' + ' '.join(cmd))
                            await reaction_cmd(cmd, user, message, payload)
            else:
                debug(f'Message {message.id} does not have data')
    else:
        debug(f'Guild {message.channel.guild.id} does not have data')

async def msg_command(message: discord.Message):
    msg_text = message.content.removeprefix('$').split(' ')
    mt0 = msg_text[0]
    if mt0 == 'hello':
        await message.reply(f'Hello, <@{message.author.id}>!')
    elif mt0 == 'hug':
        await message.add_reaction('🫂')
    elif mt0 == 'add_reply_command':
        if not message.author.guild_permissions.manage_guild:
            await message.channel.send('You need permission to manage guild in order to use this command!')
        message_id_to_apply = msg_text[1]
        debug(f'applying to {message_id_to_apply}')
        emoji_to_apply = msg_text[2]
        command = msg_text
        command.pop(0)
        command.pop(0)
        command.pop(0)
        message_to_apply = await message.channel.fetch_message(message_id_to_apply)
        await message_to_apply.add_reaction(emoji_to_apply)
        # Add to data
        debug(message.channel.guild.id)
        if not str(message.channel.guild.id) in data.keys():
            data[str(message.channel.guild.id)] = {
                message.channel.id: {
                    message.id: {
                        'reaction-commands': {
                            emoji_to_apply: [command]
                        }
                    }
                }
            }
        elif not str(message.channel.id) in data[str(message.channel.guild.id)].keys():
            data[str(message.channel.guild.id)][str(message.channel.id)] = {
                message_id_to_apply: {
                    'reaction-commands': {
                        emoji_to_apply: [command]
                    }
                }
            }
        elif not message_id_to_apply in data[str(message.channel.guild.id)][str(message.channel.id)].keys():
            data[str(message.channel.guild.id)][str(message.channel.id)][message_id_to_apply] = {
                'reaction-commands': {
                    emoji_to_apply: [command]
                }
            }
        elif not 'reaction-commands' in data[str(message.channel.guild.id)][str(message.channel.id)][message_id_to_apply].keys():
            data[str(message.channel.guild.id)][str(message.channel.id)][message_id_to_apply]['reaction-commands'] = {
                emoji_to_apply: [command]
            }
        elif not emoji_to_apply in data[str(message.channel.guild.id)][str(message.channel.id)][message_id_to_apply]['reaction-commands'].keys():
            data[str(message.channel.guild.id)][str(message.channel.id)][message_id_to_apply]['reaction-commands'][emoji_to_apply] = [command]
        elif not command in data[str(message.channel.guild.id)][str(message.channel.id)][message_id_to_apply]['reaction-commands'][emoji_to_apply]:
            data[str(message.channel.guild.id)][str(message.channel.id)][message_id_to_apply]['reaction-commands'][emoji_to_apply].append(command)
        with open(f'./data/{message.channel.guild.id}.json', 'w') as file:
            file.write(json.dumps(data[str(message.channel.guild.id)]))
            file.close()
        await message.reply('Done!')
    else:
        await message.reply(f'Invalid command: {msg_text[0]}')

async def reaction_cmd(cmd: list[str], user: discord.User | discord.Member, message: discord.Message, payload: discord.RawReactionActionEvent):
    channel = message.channel
    if cmd[0] == 'setname':
        cmd.pop(0)
        newname: str = ' '.join(cmd)
        #user.display_name = newname
        try:
            await user.edit(nick=newname)
        except discord.Forbidden:
            await channel.send('I do not have permission to update usernames of users')
        except discord.discord.HTTPException as e:
            print(e)
    elif cmd[0] == 'setrandomname':
        debug('Setting random name...')
        #user.display_name = random_name()
        try:
            await user.edit(nick=random_name())
        except discord.Forbidden:
            await channel.send('I do not have permission to update usernames of users')
        except discord.discord.HTTPException as e:
            print(e)
    elif cmd[0] == 'addrole':
        debug('Adding role to user...')
        role_id = int(cmd[1])
        try:
            await user.add_roles(channel.guild.get_role(role_id), reason=f'Reaction to message {message.id} in channel {channel.name}')
        except discord.Forbidden:
            await channel.send('I do not have permission to add roles to users')
        except discord.discord.HTTPException as e:
            print(e)
    elif cmd[0] == 'remrole':
        debug('Removing role from user...')
        role_id = int(cmd[1])
        try:
            await user.remove_roles(channel.guild.get_role(role_id), reason=f'Reaction to message {message.id} in channel {channel.name}')
        except discord.Forbidden:
            await channel.send('I do not have permission to remove roles from users')
        except discord.discord.HTTPException as e:
            print(e)
    elif cmd[0] == 'togrole':
        debug('Toggling role of user...')
        role_id = int(cmd[1])
        if channel.guild.get_role(role_id) in user.roles:
            try:
                await user.remove_roles(channel.guild.get_role(role_id), reason=f'Reaction to message {message.id} in channel {channel.name}')
            except discord.Forbidden:
                await channel.send('I do not have permission to remove roles from users')
            except discord.discord.HTTPException as e:
                print(e)
        else:
            try:
                await user.add_roles(channel.guild.get_role(role_id), reason=f'Reaction to message {message.id} in channel {channel.name}')
            except discord.Forbidden:
                await channel.send('I do not have permission to add roles to users')
            except discord.discord.HTTPException as e:
                print(e)
    elif cmd[0] == 'remove_reaction':
        try:
            await message.remove_reaction(payload.emoji, user)
        except discord.Forbidden:
            await channel.send('I do not have permission to remove reactions from messages')
        except discord.discord.HTTPException as e:
            print(e)
    else:
        await channel.send(f'ERR: Invalid command {cmd[0]}')
        

def random_name() -> str:
    return random_word_list[random.randrange(0,len(random_word_list)-1)] + random_word_list[random.randrange(0,len(random_word_list)-1)] + str(random.randrange(0,999))

client.run(discord_token)