import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "money.json"

def load_money():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_money(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_money(guild_id, user_id):
    data = load_money()
    return data.get(str(guild_id), {}).get(str(user_id), 0)

def add_money(guild_id, user_id, amount):
    data = load_money()
    gid = str(guild_id)
    uid = str(user_id)

    if gid not in data:
        data[gid] = {}

    data[gid][uid] = data[gid].get(uid, 0) + amount
    save_money(data)

suits = ["♠", "♥", "♦", "♣"]
ranks = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

def create_deck():
    deck = [(r, s) for s in suits for r in ranks]
    random.shuffle(deck)
    return deck

def card_value(card):
    if card[0] in ["J","Q","K"]:
        return 10
    if card[0] == "A":
        return 11
    return int(card[0])

def calculate_score(hand):
    score = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[0] == "A")
    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score

def format_hand(hand):
    return " ".join([f"{c[0]}{c[1]}" for c in hand])

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

@bot.command()
async def 돈추가(ctx, member: discord.Member, amount: int):
    if not is_admin(ctx):
        await ctx.send("관리자만 가능")
        return
    add_money(ctx.guild.id, member.id, amount)
    await ctx.send(f"{member.mention} +{amount}원")

@tree.command(name="내정보", description="내 돈 확인")
async def myinfo(interaction: discord.Interaction):
    money = get_money(interaction.guild.id, interaction.user.id)
    await interaction.response.send_message(
        f"{interaction.user.mention} 💰 {money}원"
    )

class BlackjackView(discord.ui.View):
    def __init__(self, ctx, bet, deck, player, dealer):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
        self.deck = deck
        self.player = player
        self.dealer = dealer

    def get_msg(self):
        return (
            f"너: {format_hand(self.player)} ({calculate_score(self.player)})\n"
            f"딜러: {self.dealer[0][0]}{self.dealer[0][1]} ??"
        )

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return

        self.player.append(self.deck.pop())

        if calculate_score(self.player) > 21:
            add_money(self.ctx.guild.id, self.ctx.author.id, -self.bet)
            await interaction.response.edit_message(
                content=f"{format_hand(self.player)} → 버스트 -{self.bet}",
                view=None
            )
            return

        await interaction.response.edit_message(
            content=self.get_msg(),
            view=self
        )

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return

        while True:
            score = calculate_score(self.dealer)
            if score < 17:
                self.dealer.append(self.deck.pop())
                continue
            if score < 19 and random.random() < 0.35:
                self.dealer.append(self.deck.pop())
                continue
            break

        p = calculate_score(self.player)
        d = calculate_score(self.dealer)

        result = f"너: {format_hand(self.player)} ({p})\n딜러: {format_hand(self.dealer)} ({d})\n"

        if d > 21 or p > d:
            add_money(self.ctx.guild.id, self.ctx.author.id, self.bet)
            result += f"승 +{self.bet}"
        elif p < d:
            add_money(self.ctx.guild.id, self.ctx.author.id, -self.bet)
            result += f"패 -{self.bet}"
        else:
            result += "무승부"

        await interaction.response.edit_message(content=result, view=None)

@bot.command()
async def 블랙잭(ctx, bet: int):
    if get_money(ctx.guild.id, ctx.author.id) < bet:
        await ctx.send("돈 부족")
        return

    deck = create_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]

    view = BlackjackView(ctx, bet, deck, player, dealer)
    await ctx.send(view.get_msg(), view=view)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"로그인됨: {bot.user}")

bot.run("YOUR_DISCORD_BOT_TOKEN")
