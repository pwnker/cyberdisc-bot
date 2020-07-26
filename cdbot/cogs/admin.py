import re
import time
from datetime import datetime
from collections import deque
from discord import AuditLogAction, Member
from discord.ext.commands import Bot, Cog

from cdbot.constants import (
    ADMIN_MENTOR_ROLE_ID,
    ADMIN_ROLES,
    BANNED_DOMAINS,
    BANNED_WORDS,
    CD_BOT_ROLE_ID,
    NICKNAME_PATTERNS,
    PLACEHOLDER_NICKNAME,
    STATIC_NICKNAME_ROLE_ID,
)


def check_bad_name(nick):
    for i in NICKNAME_PATTERNS:
        if re.match(i, nick, re.IGNORECASE):
            return True
    return False


timestamps = deque([], maxlen=4)
message_ids = deque([], maxlen=4)
user_dict = {}




class Admin(Cog):
    """
    Admin functionality
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()  # triggered on new/removed nickname
    async def on_member_update(self, member_before: Member, member_after: Member):
        # get corresponding audit log entry to find who initiated member change
        corresponding_audit_entry = None
        # get all audit log entries for Member Updated
        async for entry in self.bot.guilds[0].audit_logs(
                action=AuditLogAction.member_update
        ):
            # if this entry was to the user in question, and was this specific nickname change
            if entry.target == member_before and entry.after.nick == member_after.nick:
                corresponding_audit_entry = entry
                print(entry.user)
                print(entry.user.roles)
                break

        if (
                corresponding_audit_entry is not None
        ):  # successfully found audit log entry before
            # user changed their own nickname; ignore if admin/bot changed it
            admin_role_check = (
                    corresponding_audit_entry.user.top_role.name in ADMIN_ROLES
            )
            bot_role_check = (
                    corresponding_audit_entry.user.top_role.id == CD_BOT_ROLE_ID
            )
            mentor_role_check = (
                    corresponding_audit_entry.user.top_role.id == ADMIN_MENTOR_ROLE_ID
            )
            if not (admin_role_check or bot_role_check or mentor_role_check):
                for i in member_after.roles:
                    print(i.id)
                    if i.id == STATIC_NICKNAME_ROLE_ID:  # user has Static Name role
                        await member_after.edit(
                            nick=member_before.display_name
                        )  # revert nickname
                        return
                    else:  # check for bad words
                        new_nickname = member_after.display_name
                        if check_bad_name(new_nickname):  # bad display name
                            if not check_bad_name(
                                    member_after.name
                            ):  # username is okay
                                await member_after.edit(nick=None)  # reset nickname
                            else:
                                # assign placeholder nickname
                                await member_after.edit(nick=PLACEHOLDER_NICKNAME)

    @Cog.listener()  # triggered on username change
    async def on_user_update(self, member_before: Member, member_after: Member):
        new_username = member_after.name
        if check_bad_name(new_username):  # bad username
            # assign placeholder nickname
            await member_after.edit(nick=PLACEHOLDER_NICKNAME)

    @Cog.listener()
    async def on_member_join(self, member: Member):
        username = member.name
        if check_bad_name(username):  # bad username
            # assign placeholder nickname
            await member.edit(nick=PLACEHOLDER_NICKNAME)

    @Cog.listener()
    async def on_message(self, message):

        if not message.author.bot:
            # Checks if message contains banned word.
            for word in BANNED_WORDS:
                if re.match(f'\W{word}\W', message.content):
                    await message.delete()
                    await message.channel.send(f"{message.author.mention} Watch your language!", delete_after=5)
            # Checks if message contains banned domain.
            if any([word in message.content for word in BANNED_DOMAINS]):
                await message.delete()
                await message.channel.send(f"{message.author.mention} No invite links!", delete_after=5)
            # Checks if message contains mass mention.
            elif len(message.mentions) > 8:
                await message.delete()
                await message.channel.send(f"{message.author.mention} Don't spam mentions!", delete_after=5)
            # Checks if message was sent too quickly.
            user_dict.setdefault(str(message.author.id) + "_timestamps", timestamps).append((message.created_at.timestamp()))
            user_dict.setdefault(str(message.author.id) + "_message_id", message_ids).append(message.id)

            print(list(user_dict.get(str(message.author.id) + "_message_id")))
            # print(user_dict)
            # print(int(time.time() - min(user_dict.get(str(message.author.id) + "_timestamps", [float('inf')]))))
            # print(message_ids)
            if int(time.time() - min(user_dict.get(str(message.author.id) + "_timestamps", [float('inf')]))) < 3601:
                await message.channel.send(f"{message.author.mention} You're sending messages too fast!", delete_after=5)
                for x in list(user_dict.get(str(message.author.id) + "_message_id")):
                    await self.bot.http.delete_message(message.channel.id, x)





def setup(bot):
    bot.add_cog(Admin(bot))
