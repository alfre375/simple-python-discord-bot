import json
from uuid import uuid4
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
        return
    
    if str(message.channel.guild.id) in data.keys():
        if str(message.channel.id) in data[str(message.channel.guild.id)].keys():
            if 'onmsg-trigger' in data[str(message.channel.guild.id)][str(message.channel.id)].keys():
                if 'exclude_roles' in data[str(message.channel.guild.id)][str(message.channel.id)]['onmsg-trigger'].keys():
                    for roleid in data[str(message.channel.guild.id)][str(message.channel.id)]['onmsg-trigger']['exclude_roles']:
                        if message.guild.get_role(roleid) in message.author.roles:
                            debug(f'Ignoring because of global role exception for role {roleid}')
                if 'actions' in data[str(message.channel.guild.id)][str(message.channel.id)]['onmsg-trigger'].keys():
                    for triggerid in data[str(message.channel.guild.id)][str(message.channel.id)]['onmsg-trigger']['actions']:
                        act = data[str(message.channel.guild.id)][str(message.channel.id)]['onmsg-trigger']['actions'][triggerid]
                        action = act['action']
                        action_specific = act['action_specific']
                        
                        match action:
                            case 'ban':
                                try:
                                    await message.author.ban(
                                        delete_message_seconds=10,
                                        reason=action_specific
                                    )
                                except discord.errors.Forbidden:
                                    await message.reply("The action 'ban' has failed due to insufficient permissions")
                            case 'kick':
                                try:
                                    await message.author.kick(
                                        reason=action_specific
                                    )
                                except discord.errors.Forbidden:
                                    await message.reply("The action 'kick' has failed due to insufficient permissions")
                            case 'sendmsg':
                                await message.channel.send(action_specific)
                            case 'addrole':
                                await message.author.add_roles(message.channel.guild.get_role(action_specific))

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
    if not (message.channel.permissions_for(message.guild.me).send_messages):
        print(f"Lacking send message permission in guild {message.guild.id}")
        return
    
    msg_text = message.content.removeprefix('$').split(' ')
    mt0 = msg_text[0]
    msg_channel = message.channel
    if mt0 == 'hello':
        await message.reply(f'Hello, <@{message.author.id}>!')
    elif mt0 == 'hug':
        await message.add_reaction('🫂')
    elif mt0 == 'add_reply_command':
        if not checkPermission('add_reply_command', message.author, message.channel):
            await message.reply('You need permission to manage guild or an allowed role in order to use this command!')
            return
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
    elif mt0 == 'add_channel_onmsg_trigger':
        if not message.author.guild_permissions.manage_guild:
            await message.reply('You need permission to manage guild in order to use this command!')
            return
        action = msg_text[1] if len(msg_text) > 1 else None
        action_specific = ' '.join(msg_text[2:]) if len(msg_text) > 2 else None
        trigger_id = str(uuid4())
        
        match action:
            case 'sendmsg':
                if not action_specific:
                    await message.reply('The sendmsg action requires the message content to send to be specified.')
                    return
            case 'addrole':
                if not action_specific:
                    await message.reply('The role to add must be specifed.')
            case _:
                if not action in ['ban', 'kick']:
                    await message.reply('Invalid action.')
        
        debug(f'Data: {data}\nKeys: {data.keys()}')
        if not str(msg_channel.guild.id) in data.keys():
            debug('Guild ' + str(msg_channel.guild.id) + ' has not yet been initialised; initialising')
            data[str(msg_channel.guild.id)] = {
                msg_channel.id: {
                    'onmsg-trigger': {
                        'actions': {
                            trigger_id: {
                                'action': action,
                                'action_specific': action_specific,
                                'exclude_roles': [],
                                'exclude_users': [],
                            }
                        }
                    }
                }
            }
        elif not str(msg_channel.id) in data[str(msg_channel.guild.id)].keys():
            debug('Channel ' + str(msg_channel.id) + ' has not yet been initialised; initialising')
            data[str(msg_channel.guild.id)][str(msg_channel.id)] = {
                'onmsg-trigger': {
                    'actions': {
                        trigger_id: {
                            'action': action,
                            'action_specific': action_specific,
                            'exclude_roles': [],
                            'exclude_users': [],
                        }
                    }
                }
            }
        elif not ('onmsg-trigger') in data[str(msg_channel.guild.id)][str(msg_channel.id)].keys():
            debug('Channel did not previously have any onmsg-trigger values')
            data[str(msg_channel.guild.id)][str(msg_channel.id)]['onmsg-trigger'] = {
                'actions': {
                    trigger_id: {
                        'action': action,
                        'action_specific': action_specific,
                        'exclude_roles': [],
                        'exclude_users': [],
                    }
                }
            }
        elif not ('actions') in data[str(msg_channel.guild.id)][str(msg_channel.id)]['onmsg-trigger'].keys():
            debug('Channel did not previously have a list of actions for onmsg-trigger')
            data[str(msg_channel.guild.id)][str(msg_channel.id)]['onmsg-trigger']['actions'] = {
                trigger_id: {
                    'action': action,
                    'action_specific': action_specific,
                    'exclude_roles': [],
                    'exclude_users': [],
                }
            }
        elif not str(trigger_id) in data[str(msg_channel.guild.id)][str(msg_channel.id)]['onmsg-trigger']['actions'].keys():
            debug(f'Adding trigger of id {trigger_id} to channel {msg_channel.id} of server {msg_channel.guild.id}')
            data[str(msg_channel.guild.id)][str(msg_channel.id)]['onmsg-trigger']['actions'][trigger_id] = {
                'action': action,
                'action_specific': action_specific,
                'exclude_roles': [],
                'exclude_users': [],
            }
        else:
            await message.reply(f'The ID ({trigger_id}) we assigned you is already used in this channel for an onmsg-trigger. Please try again.')
            return
        await message.reply(f'Successfuly added onmsg trigger with ID {trigger_id}')
        with open(f'./data/{message.channel.guild.id}.json', 'w') as file:
            debug(data)
            file.write(json.dumps(data[str(message.channel.guild.id)]))
            file.close()
    elif mt0 == 'edit_channel_onmsg_trigger':
        if not message.author.guild_permissions.manage_guild:
            await message.reply('You need permission to manage guild in order to use this command!')
            return
        
        if len(msg_text) < 2:
            await message.reply('You must specify an onmsg_trigger')
            return
        if len(msg_text) < 3:
            await message.reply('You must specify an action')
            return
        
        trigger_id = msg_text[1]
        action = msg_text[2]
        
        if not (
            (str(msg_channel.guild.id) in data.keys()) and
            (str(msg_channel.id) in data[str(msg_channel.guild.id)].keys()) and
            ('onmsg-trigger' in data[str(msg_channel.guild.id)][str(msg_channel.id)].keys()) and
            ('actions' in data[str(msg_channel.guild.id)][str(msg_channel.id)]['onmsg-trigger'].keys()) and
            (trigger_id in data[str(msg_channel.guild.id)][str(msg_channel.id)]['onmsg-trigger']['actions'].keys())
            ):
            await message.reply('Invalid trigger ID (make sure you are in the correct channel)')
            return
        
        match action:
            case 'del':
                data[str(msg_channel.guild.id)][str(msg_channel.id)]['onmsg-trigger']['actions'].pop(trigger_id)
                await message.reply(f'Successfuly deleted trigger {trigger_id} in channel {msg_channel.id}')
            case _:
                await message.reply(f'Invalid action: {action}')
        
        with open(f'./data/{message.channel.guild.id}.json', 'w') as file:
            debug(data)
            file.write(json.dumps(data[str(message.channel.guild.id)]))
            file.close()
    elif mt0 == 'list_channel_onmsg_triggers':
        if not message.author.guild_permissions.manage_guild:
            await message.reply('You need permission to manage guild in order to use this command!')
            return
            
        applicable_channel = int(msg_text[1], base=0) if len(msg_text) > 1 else message.channel.id
        
        if not (
            (str(msg_channel.guild.id) in data.keys()) and
            (str(applicable_channel) in data[str(msg_channel.guild.id)].keys()) and
            ('onmsg-trigger' in data[str(msg_channel.guild.id)][str(applicable_channel)].keys()) and
            ('actions' in data[str(msg_channel.guild.id)][str(applicable_channel)]['onmsg-trigger'].keys()) and
            (len(data[str(msg_channel.guild.id)][str(applicable_channel)]['onmsg-trigger']['actions'].keys()) > 0)
            ):
            await message.reply('There are no onmsg_triggers in this channel')
            return
        
        await message.reply('The list of onmsg_triggers in this channel is as follows:\n- ' + '\n- '.join(list(data[str(msg_channel.guild.id)][str(applicable_channel)]['onmsg-trigger']['actions'].keys())))
    elif mt0 == 'add_onmsg_trigger_channel_role_exception':
        if not message.author.guild_permissions.manage_roles:
            await message.reply('You need permission to manage roles in order to use this command!')
            return
        
        if len(msg_text) < 2:
            await message.reply('ERROR: Must specify role as role ID')
            return
        
        applicable_channel = int(msg_text[2], base=0) if len(msg_text) > 2 else message.channel.id
        
        role: discord.Role = message.guild.get_role(int(msg_text[1]))
        
        if not role:
            await message.reply('ERROR: invalid role')
            return
        
        if not str(msg_channel.guild.id) in data.keys():
            data[str(msg_channel.guild.id)] = {
                str(applicable_channel): {
                    'onmsg-trigger': {
                        'exclude_roles': [
                            int(msg_text[1])
                        ]
                    }
                }
            }
        elif not str(applicable_channel) in data[str(msg_channel.guild.id)].keys():
            data[str(msg_channel.guild.id)][str(applicable_channel)] = {
                'onmsg-trigger': {
                    'exclude_roles': [
                        int(msg_text[1])
                    ]
                }
            }
        elif not 'onmsg-trigger' in data[str(msg_channel.guild.id)][str(applicable_channel)].keys():
            data[str(msg_channel.guild.id)][str(applicable_channel)]['onmsg-trigger'] = {
                'exclude_roles': [
                    int(msg_text[1])
                ]
            }
        elif not 'exclude_roles' in data[str(msg_channel.guild.id)][str(applicable_channel)]['onmsg-trigger'].keys():
            data[str(msg_channel.guild.id)][str(applicable_channel)]['onmsg-trigger']['exclude_roles'] = [
                int(msg_text[1])
            ]
        elif not msg_text[1] in data[str(msg_channel.guild.id)][str(applicable_channel)]['onmsg-trigger']['exclude_roles'].keys():
            data[str(msg_channel.guild.id)][str(applicable_channel)]['onmsg-trigger']['exclude_roles'].push(int(msg_text[1]))
        else:
            await message.reply('Role has already been added to this channel\'s global onmsg-trigger role exclusions')
            return
        await message.reply(f'Added role {role.name} (ID: {role.id}) to this channel\'s global onmsg-trigger role exclusions')
    elif mt0 == 'say_as_bot':
        if not checkPermission('say_as_bot', message.author, message.channel):
            await message.reply('You do not have permissions to say this as the bot')
            return
        shall_send_val = ' '.join(msg_text[1:])
        await message.channel.send(shall_send_val)
        await message.delete()
        #log(message.guild, f'User <@{message.author.id}> made the bot say {shall_send_val}')
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
        
def checkPermission(permission: str, user: discord.Member, channel: discord.channel.TextChannel):
    if user.guild_permissions.manage_guild:
        return True
    guild_id = str(channel.guild.id)
    if guild_id in data:
        debug('Guild registered')
        if 'role_permissions' in data[guild_id]:
            debug('Guild has role permissions')
            for role in user.roles:
                role_id = str(role.id)
                debug(f'Trying role {role.name} ({role_id})')
                if role_id in data[guild_id]['role_permissions']:
                    debug('Permissions registered for this role')
                    if permission in data[guild_id]['role_permissions'][role_id]:
                        debug('This role has the specified permission')
                        return True
                    if 'universal' in data[guild_id]['role_permissions'][role_id]:
                        debug('This role has the universal permission')
                        return True
    return False

def random_name() -> str:
    return random_word_list[random.randrange(0,len(random_word_list)-1)] + random_word_list[random.randrange(0,len(random_word_list)-1)] + str(random.randrange(0,999))

client.run(discord_token)