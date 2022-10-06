from disnake.ext import commands
from disnake.ext.bridge.context import BridgeApplicationContext
from disnake.ext.commands import slash_command, Embed, Color, Member, Object, utils
import typing
import asyncio
from disnake.ext.commands.cooldowns import BucketType
import ksoftapi
from bot import Atomic, HeirarchyErrorType

kclient = ksoftapi.Client("fef9dba21ffb0adbec3337bbc0ac4a6ee74dcc11")


def has_voted():
    async def predicate(ctx):
        # if not await ctx.bot.dbl.get_user_vote(ctx.author.id):
        #     embed=Embed(title="That's a voter-only command!",description="You can't use this command without voting! Use the `vote` command to vote for me and unlock this command!",color=Color.blue())
        #     await ctx.send(embed=embed)
        # return await ctx.bot.dbl.get_user_vote(ctx.author.id)
        return True

    return commands.check(predicate)


class Moderation(commands.Cog):
    def __init__(self, bot: Atomic):
        self.bot = bot
        # self.dbl = bot.dbl

    @slash_command(
        name="scan",
        description="Checks your member list against the KSoft.Si bans list.",
        usage="scan [options]",
    )
    @commands.has_permissions(manage_guild=True, ban_members=True)
    @commands.bot_has_permissions(ban_members=True, kick_members=True)
    @commands.max_concurrency(1, per=BucketType.default, wait=True)
    @has_voted()
    async def scan(self, ctx: BridgeApplicationContext, *args):
        await ctx.response.send_message(
            f"Beginning Scan... Estimated Duration: {len(ctx.guild.members)*3} seconds"
        )
        for i in ctx.guild.members:
            if not i.bot:
                if await kclient.bans.check(i.id):
                    ban = await kclient.bans.info(i.id)
                    embed = Embed(
                        title=f"⚠ {i} is banned from KSoft!",
                        description=f"User was banned for {ban.reason}. ([proof]({ban.proof}))",
                        color=Color.red(),
                    )
                    await ctx.send(embed=embed)
                    if "-ban" in args or "-b" in args:
                        await ctx.guild.ban(
                            i,
                            reason=f"Banned by {ctx.author} through scan command.",
                            delete_message_days=0,
                        )
                        await asyncio.sleep(5)
                        break
                    elif "-kick" in args or "-k" in args:
                        await ctx.guild.kick(
                            i, reason=f"Kicked by {ctx.author} through scan command."
                        )
                await asyncio.sleep(3)
        await ctx.send("Scan complete!")

    @scan.error
    async def on_error(ctx: BridgeApplicationContext, e):
        if isinstance(e, commands.MaxConcurrencyReached):
            embed = Embed(
                title="This command is currently being used by someone else!",
                description="We'll run the command when it's ready, and notify you when the command is running!",
                color=Color.green(),
            )
            await ctx.send(embed=embed)
            ctx.from_concurrency = True

    @slash_command(
        name="lock",
        description="Locks the channel for a specified amount of time.",
        aliases=["lockdown", "close"],
        usage="lock",
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(
        self,
        ctx: BridgeApplicationContext,
        time="infinite",
        *,
        reason="No Reason Provided.",
    ):
        if time == "infinite":
            seconds, time = self.bot.calculate_time(time)
        else:
            formatendtime = "further notice"
        embed = Embed(
            title="This channel was locked 🔒",
            description=f"This channel was locked down for reason: {reason}",
            color=Color.red(),
        )
        embed.set_footer(
            text=f"This channel is locked until {formatendtime} ● Responsible Moderator: {ctx.author.name}"
        )
        msg = await ctx.send(embed=embed)
        guildroles = await ctx.guild.fetch_roles()
        everyone = utils.get(guildroles, name="@everyone")
        await ctx.channel.set_permissions(
            everyone, send_messages=False, read_messages=True
        )
        if time != "infinite":
            await asyncio.sleep(seconds)
            embed = Embed(
                title="This channel is now unlocked 🔓",
                description=f"This channel is now unlocked.",
                color=Color.blue(),
            )
            embed.set_footer(text=f"This channel was unlocked at {formatendtime}.")
            await ctx.channel.set_permissions(everyone, overwrite=None)
            await msg.edit(embed=embed)

    @slash_command(
        name="unlock",
        description="Unlocks a channel, making it so that members can type again.",
        aliases=["unlockdown", "open"],
        usage="unlock",
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        guildroles = await ctx.guild.fetch_roles()
        everyone = utils.get(guildroles, name="@everyone")
        await ctx.channel.set_permissions(everyone, overwrite=None)
        embed = Embed(
            title="This channel was unlocked",
            description=f"This channel is now unlocked.",
        )
        await ctx.send(embed=embed)

    @slash_command(
        name="clean",
        description="Cleans x messages in a channel.",
        aliases=["c", "wipe"],
        usage="clean <number>",
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clean(
        self,
        ctx: BridgeApplicationContext,
        amount=2,
        *,
        member: typing.Optional[Member],
    ):
        if member:

            def check(m):
                return m.author == member

        else:
            check = lambda m: True
        await ctx.channel.purge(limit=amount + 1, bulk=True, check=check)
        delmsg = await ctx.channel.send(
            str(amount)
            + " messages cleaned. This message will be deleted in 3 seconds."
        )
        await asyncio.sleep(3)
        await delmsg.delete()

    @slash_command(
        name="kick", description="Kicks a user", aliases=["k"], usage="kick <user>"
    )
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: BridgeApplicationContext,
        member: Member,
        *,
        reason="No reason provided",
    ):
        if (
            member.top_role >= ctx.author.top_role
            and ctx.guild.owner_id != ctx.author.id
        ):
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above yours, you've been H E I R A R C H Y ' D"
            )
        if member.top_role.position >= ctx.guild.me.top_role.position:
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above mine, I've been H E I R A R C H Y ' D"
            )
        else:
            try:
                await member.send(
                    f"You have been kicked from {ctx.guild.name} for: \n" + reason
                )
            except:
                await ctx.send("The member has their DMs closed. I still will kick...")
            await member.kick(reason=reason)
            await ctx.send(str(member) + " just got the boot. :boot: :sunglasses:")

    @slash_command(
        name="warn", description="Warns a user", aliases=["w"], usage="warn user>"
    )
    @commands.has_permissions(kick_members=True)
    async def warn(
        self,
        ctx: BridgeApplicationContext,
        member: Member,
        *,
        reason="No reason provided",
    ):
        if type(member) == Member:
            c = self.bot.check_heirarchy(ctx, member)
            if c == HeirarchyErrorType.NO_PERMISSION:
                return await ctx.send(
                    f"whoops... {member.name}'s highest role is above yours, you can't complete this action"
                )
            elif c == HeirarchyErrorType.SELF_NO_PERMISSION:
                return await ctx.send(
                    f"whoops... {member.name}'s highest role is above mine, i can't complete this action. maybe try talking to the server owner?"
                )
        else:
            try:
                await member.send(
                    f"you've been warned in {ctx.guild.name} for: {reason}"
                )
            except:
                await ctx.response.send_message("the member has their DMs closed.")

    @slash_command(
        name="ban", description="Bans a user", aliases=["b"], usage="ban <user>"
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: BridgeApplicationContext,
        member: Member,
        *,
        reason="no reason provided",
    ):
        c = self.bot.check_heirarchy(ctx.author, member)
        if c == HeirarchyErrorType.NO_PERMISSION:
            return await ctx.send(
                f"whoops... {member.name}'s highest role is above yours, you can't complete this action"
            )
        elif c == HeirarchyErrorType.SELF_NO_PERMISSION:
            return await ctx.send(
                f"whoops... {member.name}'s highest role is above mine, i can't complete this action. maybe try talking to the server owner?"
            )
        else:
            try:
                user = await self.bot.fetch_user(member.id)
                await user.send(
                    f"the **ban hammer** has spoken to you in {ctx.guild.name} with reason: {reason}"
                )
            except:
                await ctx.guild.ban(member, reason=reason)

    @slash_command(
        name="unban", description="Unbans a user", aliases=["ub"], usage="unban <user>"
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: BridgeApplicationContext, *, member: Object):
        try:
            user = await self.bot.fetch_user(member.id)
        except:
            user = None
        try:
            await ctx.guild.unban(member)
        except:
            await ctx.send(
                f"{user.name} doesn't appear to be banned."
            ) if not user else await ctx.send(
                f"{member.id} doesn't appear to be banned."
            )
        try:
            user.send("You have been unbanned from " + ctx.guild.name)
        except:
            pass
        await ctx.send(user + " has been unbanned from " + ctx.guild.name)

    @slash_command(
        name="mute",
        description="Mutes a user. In other words, removes their ability to chat.",
        aliases=["m"],
        usage="mute <user>",
    )
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def mute(
        self,
        ctx: BridgeApplicationContext,
        member: Member,
        *,
        reason="No reason provided",
    ):
        if (
            member.top_role >= ctx.author.top_role
            and ctx.guild.owner_id != ctx.author.id
        ):
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above yours, you've been H E I R A R C H Y ' D"
            )
        if member.top_role.position >= ctx.guild.me.top_role.position:
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above mine, I've been H E I R A R C H Y ' D"
            )
        else:
            await ctx.message.add_reaction("🔇")
            try:
                await member.send(
                    "You have been muted in " + ctx.guild.name + "\nReason: " + reason
                )
            except:
                await ctx.send("User's DMs are closed. Still muting...")
            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(member, send_messages=False)
                except:
                    ctx.author.send(f"I was unable to mute in {channel.mention}.")
            await ctx.send(str(member) + " has been muted.")

    @slash_command(
        name="lockout",
        description="Locks a user out of a channel. In other words, removes their ability to see a given channel.",
        aliases=["cb"],
        usage="lockout <user>",
    )
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lockout(
        self,
        ctx: BridgeApplicationContext,
        member: Member,
        *,
        reason="No reason provided",
    ):
        if (
            member.top_role >= ctx.author.top_role
            and ctx.guild.owner_id != ctx.author.id
        ):
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above yours, you've been H E I R A R C H Y ' D"
            )
        if member.top_role.position >= ctx.guild.me.top_role.position:
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above mine, I've been H E I R A R C H Y ' D"
            )
        else:
            try:
                await member.send(
                    f"You have been locked out of {ctx.channel.name} in {ctx.guild.name}\nReason: {reason}"
                )
            except:
                pass
            await ctx.channel.set_permissions(
                member, send_messages=False, read_messages=False
            )
            await ctx.send(str(member) + " has been locked out of this channel..")

    @slash_command(
        name="unlockout",
        description="Unlocks a user out of a channel. In other words, removes their ability to see a given channel.",
        aliases=["ucb"],
        usage="unlockout <user>",
    )
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlockout(self, ctx: BridgeApplicationContext, *, member: Member):
        if (
            member.top_role >= ctx.author.top_role
            and ctx.guild.owner_id != ctx.author.id
        ):
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above yours, you've been H E I R A R C H Y ' D"
            )
        if member.top_role.position >= ctx.guild.me.top_role.position:
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above mine, I've been H E I R A R C H Y ' D"
            )
        else:
            try:
                await member.send(
                    f"You have been un-locked out of {ctx.channel.name} in {ctx.guild.name}."
                )
            except:
                pass
            await ctx.channel.set_permissions(member, overwrite=None)
            await ctx.send(str(member) + " has been unlocked from this channel..")

    @slash_command(
        name="unmute",
        description="Unmutes a user. In other words, gives them  their ability to chat back.",
        aliases=["sum", "sumute"],
        usage="unmute <user>",
    )  # still in testing...
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unmute(
        self,
        ctx: BridgeApplicationContext,
        member: Member,
        *,
        reason="No reason provided",
    ):
        if (
            member.top_role >= ctx.author.top_role
            and ctx.guild.owner_id != ctx.author.id
        ):
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above yours, you've been H E I R A R C H Y ' D"
            )
        if member.top_role.position >= ctx.guild.me.top_role.position:
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above mine, I've been H E I R A R C H Y ' D"
            )
        else:
            try:
                await member.send(
                    "You have been unmuted in " + ctx.guild.name + "\nReason: " + reason
                )
            except:
                await ctx.send("User's DMs are closed. Still unmuting...")
            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(member, overwrite=None)
                except:
                    # await ctx.send("I was unable to mute.")
                    ctx.author.send(f"I was unable to unmute in {channel.mention}.")
                    return
            await ctx.send(str(member) + " has been unmuted.")

    @slash_command(name="timeout", description="Revokes read permissions from a user.")
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    async def timeout(self, ctx: BridgeApplicationContext, member: Member):
        if (
            member.top_role >= ctx.author.top_role
            and ctx.guild.owner_id != ctx.author.id
        ):
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above yours, you've been H E I R A R C H Y ' D"
            )
        if member.top_role.position >= ctx.guild.me.top_role.position:
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above mine, I've been H E I R A R C H Y ' D"
            )
        else:
            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(
                        member, send_messages=False, read_messages=False
                    )
                    await ctx.send(str(member) + " has been put in timeout.")
                except:
                    # await ctx.send("I was unable to mute.")
                    ctx.author.send(
                        f"I was unable to timeout {member.mention} in {channel.mention}."
                    )

    @slash_command(
        name="untimeout", description="Gives read permissions back to a user."
    )
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    async def untimeout(self, ctx: BridgeApplicationContext, member: Member):
        if (
            member.top_role >= ctx.author.top_role
            and ctx.guild.owner_id != ctx.author.id
        ):
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above yours, you've been H E I R A R C H Y ' D"
            )
        if member.top_role.position >= ctx.guild.me.top_role.position:
            await ctx.send(
                f"**Erhm...** {member.name}'s highest role is above mine, I've been H E I R A R C H Y ' D"
            )
        else:
            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(member, overwrite=None)
                    await ctx.send(str(member) + " has been removed from timeout.")
                except:
                    ctx.author.send(
                        f"I was unable to un-timeout {member.mention} in {channel.mention}."
                    )

    ##============================|| UTILITY COMMANDS START HERE ||==========================##


def setup(bot):
    bot.add_cog(Moderation(bot))
