import discord
from discord.ext import commands
from utils.database import DatabaseCog
from utils.checks import is_staff, check_if_user_can_ready
import asyncio

class Newcomers(DatabaseCog):
    """
    Handles auto-probation and commands related to the newcomers channel.
    """

    on_aliases = ('on', 'true', '1', 'enable')
    off_aliases = ('off', 'false', '0', 'disable')

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.init()) # We can't do proper init here.

    async def init(self):
        await self.bot.wait_until_all_ready()
        flag_name = 'auto_probation'

        self.autoprobate = await self.get_flag(flag_name)

        if self.autoprobate is None:
            self.autoprobate = False
            await self.add_flag(flag_name)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.autoprobate:
            await member.add_roles(self.bot.roles['Probation'], reason="Auto-probation")

    async def autoprobate_handler(self, ctx, enabled:bool=None):
        if enabled is not None:
            self.autoprobate = enabled
            await self.set_flag('auto_probation', enabled)

        inactive_text = f'**inactive**. ⚠️\nTo activate it, use `.autoprobate {" | ".join(self.on_aliases)}`.'
        active_text = f'**active**. ✅\nTo deactivate it, use `.autoprobate {" | ".join(self.off_aliases)}`.'
        await ctx.send(f'🔨 Auto-probation is {active_text if self.autoprobate else inactive_text}')

    @is_staff('Helper')
    @commands.group(invoke_without_command=True, case_insensitive=True)
    async def autoprobate(self, ctx):
        """
        Manages auto-probation.
        on | true | 1 | enable: turns on auto-probation.
        off | false | 0 | disable: turns off auto-probation.
        To display the status of auto-probation, invoke with no subcommand.
        """
        await self.autoprobate_handler(ctx)

    @is_staff('OP')
    @autoprobate.command(aliases=on_aliases, hidden=True)
    async def autoprobate_on(self, ctx):
        await self.autoprobate_handler(ctx, True)

    @is_staff('OP')
    @autoprobate.command(aliases=off_aliases, hidden=True)
    async def autoprobate_off(self, ctx):
        await self.autoprobate_handler(ctx, False)

    @is_staff('OP')
    @commands.guild_only()
    @commands.command()
    async def ncprune(self, ctx, days:int=7):
        await ctx.guild.prune_members(days=days, compute_prune_count=False, roles=[self.bot.roles['Probation']], reason='Auto-probation pruning')
        await ctx.send('Prune complete. ✅')

    @check_if_user_can_ready()
    @commands.guild_only()
    @commands.command(aliases=['ready'])
    @commands.max_concurrency(1, commands.BucketType.channel)
    async def ncready(self, ctx, *, reason=""):
        """Alerts online staff to a ready request in newcomers."""
        cooldown = 300
        newcomers = self.bot.channels['newcomers']
        reason = reason[:500] # truncate to 500 chars so kurisu doesn't send absurdly huge messages

        await ctx.message.delete()
        if reason:
            await newcomers.send(f'{ctx.author} (ID: {ctx.author.id}) is ready for unprobation.\n\nMessage: `{reason}` @here', allowed_mentions=discord.AllowedMentions(everyone=True))
            await newcomers.send(f'This command will be usable again in {cooldown} seconds.', delete_after=cooldown)
            try:
                await ctx.author.send('✅ Online staff have been notified of your request.')
            except discord.errors.Forbidden:
                pass
        else:
            cooldown = 30
            await newcomers.send(f'{ctx.author.mention}, please run this command again in {cooldown} seconds \
with a brief message explaining your situation (e.g., `.ready hey guys, i was having trouble hacking my console`). \
**Copying and pasting the example will not remove your probation.**')

        await asyncio.sleep(cooldown)

def setup(bot):
    bot.add_cog(Newcomers(bot))

