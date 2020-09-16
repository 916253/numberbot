import aiosqlite3
import json


class Manager:
    def __init__(self, bot):
        self.dbcon = bot.holder

    @staticmethod
    def format_args(args: dict) -> str:
        if len(args) < 1:
            return ''
        separator = args.pop('separator', 'AND')
        statement = 'WHERE '
        conditions = []
        for kword, value in args.items():
            conditions.append(f"{kword} = '{value}'")
        return statement + f' {separator} '.join(conditions)


class WordFilterManager(Manager):
    def __init__(self, bot):
        super().__init__(bot)
        self.kinds = ('piracy tool', 'piracy video', 'piracy tool alert', 'drama', 'unbanning tool', 'piracy site')
        self.filter = {}

    async def load(self):
        for kind in self.kinds:
            self.filter[kind] = [i[0] for i in await self.fetch(kind=kind)]
        print("Loaded word filter")

    async def bulk_load(self):
        with open("wordfilter.json", 'r') as f:
            dict = json.load(f)
            values = []
            for kind in self.kinds:
                if kind in dict:
                    for entry in dict[kind]:
                        values.append(f"('{entry}','{kind}')")
            async with self.dbcon as cur:
                await cur.execute(f"INSERT INTO wordfilter VALUES {','.join(values)}")
            await self.load()

    async def add(self, word: str, kind: str) -> tuple:
        async with self.dbcon as cur:
            try:
                await cur.execute(f'INSERT INTO wordfilter VALUES ("{word}","{kind}")')
            except aiosqlite3.IntegrityError:
                return None, None
        await self.load()
        return word, kind

    async def fetch(self, **kwargs) -> tuple:
        cond = self.format_args(kwargs)
        async with self.dbcon as cur:
            await cur.execute(f'SELECT word FROM wordfilter {cond}')
            return await cur.fetchall()

    async def delete(self, word: str):
        if not await self.fetch(word=word):
            return None
        async with self.dbcon as cur:
            await cur.execute(f'DELETE FROM wordfilter WHERE word="{word}"')
        await self.load()
        return word


class Invite:
    def __init__(self, invite_code, remaining_uses):
        self.code = invite_code
        self.uses = remaining_uses

    @property
    def is_temporary(self):
        return self.uses > 0


class InviteFilterManager(Manager):
    def __init__(self, bot):
        super().__init__(bot)
        self.invites = {}

    async def load(self):
        self.invites.clear()
        invites = await self.fetch()
        if invites:
            for code, _, alias, uses in invites:
                self.invites[alias] = Invite(code, uses)
        print("Loaded Invites")

    async def add(self, code: str, name: str, alias: str, uses: int):
        async with self.dbcon as cur:
            try:
                await cur.execute(f"INSERT INTO invitefilter VALUES ('{code}', '{name}', '{alias}', {uses})")
            except aiosqlite3.IntegrityError:
                return None, None
        await self.load()
        return name, code

    async def fetch(self, **kwargs):
        cond = self.format_args(kwargs)
        async with self.dbcon as cur:
            await cur.execute(f'SELECT * FROM invitefilter {cond}')
            return await cur.fetchall()

    async def set_uses(self, code: str, uses: int):
        async with self.dbcon as cur:
            await cur.execute(f"UPDATE invitefilter SET remaining_uses={uses} WHERE code='{code}'")
        await self.load()

    async def delete(self, **kwargs):
        cond = self.format_args(kwargs,)
        async with self.dbcon as cur:
            await cur.execute(f'DELETE FROM invitefilter {cond}')
        await self.load()
