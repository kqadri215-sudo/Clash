import os
import io
import re
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
API_BASE = "https://api.clashk.ing"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def font(size, bold=True):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def getv(obj, *keys, default=None):
    for k in keys:
        if isinstance(obj, dict) and k in obj and obj[k] is not None:
            return obj[k]
    return default

def normalize_tag(tag):
    tag = tag.strip().upper().replace(" ", "")
    if not tag.startswith("#"):
        tag = "#" + tag
    if not re.fullmatch(r"#[A-Z0-9]+", tag):
        raise ValueError("Tag غير صحيح. مثال: #ABC123")
    return tag

async def api_json(session, path):
    async with session.get(API_BASE + path, timeout=aiohttp.ClientTimeout(total=20)) as r:
        if r.status == 404:
            return None
        if r.status >= 400:
            body = (await r.text())[:250]
            raise RuntimeError(f"API HTTP {r.status}: {body}")
        return await r.json(content_type=None)

async def fetch_player(session, tag):
    from urllib.parse import quote
    return await api_json(session, "/v2/player/" + quote(tag.lstrip("#"), safe="") )

async def fetch_legend_series(session, tag):
    from urllib.parse import quote
    return await api_json(session, "/v2/player/" + quote(tag.lstrip("#"), safe="") + "/legend/series")

async def fetch_legend_battles(session, tag, day):
    from urllib.parse import quote
    return await api_json(session, "/v2/player/" + quote(tag.lstrip("#"), safe="") + "/legend/" + quote(str(day), safe="") + "/battlelog")

def extract_battles(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("items", "battles", "battleLog", "battlelog", "attacks", "logs", "data"):
        val = data.get(key)
        if isinstance(val, list):
            return val
    # Some responses split attack and defense logs
    out = []
    for key, is_attack in (("attackLogs", True), ("attacks", True), ("defenseLogs", False), ("defenses", False)):
        val = data.get(key)
        if isinstance(val, list):
            for item in val:
                item = dict(item)
                item.setdefault("attack", is_attack)
                out.append(item)
    return out

def is_attack(entry):
    value = getv(entry, "attack", "isAttack", "is_attack")
    if isinstance(value, bool):
        return value
    kind = str(getv(entry, "type", "battleType", "mode", default="")).lower()
    return kind in ("attack", "offense", "offensive")

def battle_values(entry):
    trophies = getv(entry, "trophies", "trophyChange", "trophy_change", "change", default=0)
    stars = getv(entry, "stars", "starCount", "star_count", default=0)
    destruction = getv(entry, "destructionPercentage", "destruction", "percentage", default=None)
    opponent = getv(entry, "opponentName", "opponent", "name", "defenderName", default="Opponent")
    if isinstance(opponent, dict):
        opponent = getv(opponent, "name", "playerName", default="Opponent")
    try: trophies = int(trophies or 0)
    except (TypeError, ValueError): trophies = 0
    try: stars = int(stars or 0)
    except (TypeError, ValueError): stars = 0
    try: destruction = int(float(destruction)) if destruction is not None else None
    except (TypeError, ValueError): destruction = None
    return str(opponent), trophies, stars, destruction

def draw_star(draw, x, y, r, fill):
    pts=[]
    import math
    for i in range(10):
        a=-math.pi/2+i*math.pi/5
        rr=r if i%2==0 else r*0.45
        pts.append((x+rr*math.cos(a), y+rr*math.sin(a)))
    draw.polygon(pts, fill=fill, outline=(75,65,55))

def render_image(player, tag, day, battles):
    # Reference-inspired layout: parchment frame, maroon header, gold/grey/red tiles.
    W=1600
    margin=26
    tile_w, tile_h, gap = 104, 76, 10
    cols=12
    rows=max(1, (max(len(battles), 1)+cols-1)//cols)
    header_h=176
    H=header_h + rows*(tile_h+gap) + 42
    im=Image.new("RGB",(W,H),(56,48,43))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((12,12,W-12,H-12), radius=22, fill=(90,78,67), outline=(28,25,23), width=7)
    d.rounded_rectangle((28,28,W-28,H-28), radius=18, fill=(232,222,202), outline=(255,245,220), width=5)
    d.rounded_rectangle((42,42,W-42,header_h), radius=15, fill=(100,32,49), outline=(50,19,29), width=4)
    name=getv(player,"name",default="Player") if isinstance(player,dict) else "Player"
    trophies=getv(player,"trophies",default="?") if isinstance(player,dict) else "?"
    th=getv(player,"townHallLevel","townhallLevel","townHall",default="?") if isinstance(player,dict) else "?"
    title_font=font(36); sub_font=font(24); total_font=font(30)
    d.text((65,57), f"{name}  |  {tag}", font=title_font, fill=(255,245,218), stroke_width=1, stroke_fill=(40,20,20))
    d.text((65,108), f"Legend League • Day: {day} • TH {th} • Trophies: {trophies}", font=sub_font, fill=(255,232,184))
    attacks=[b for b in battles if is_attack(b)]
    defenses=[b for b in battles if not is_attack(b)]
    attack_total=sum(battle_values(b)[1] for b in attacks)
    defense_total=sum(battle_values(b)[1] for b in defenses)
    total=attack_total+defense_total
    d.text((W//2,58), f"TOTAL: {total:+d} 🏆", font=total_font, fill=(255,244,190), anchor="ma")
    d.text((65,145), f"ATTACKS: {attack_total:+d}   ({len(attacks)})", font=sub_font, fill=(255,245,220))
    d.text((W//2+110,145), f"DEFENSES: {defense_total:+d}   ({len(defenses)})", font=sub_font, fill=(255,245,220))
    # The reference has attacks first, defenses after them.
    ordered=attacks+defenses
    start_y=header_h+15
    for idx, entry in enumerate(ordered):
        row, col=divmod(idx,cols)
        x=margin+col*(tile_w+gap)
        y=start_y+row*(tile_h+gap)
        _, trophies_delta, stars, destruction=battle_values(entry)
        attack=idx < len(attacks)
        if attack:
            fill=(246,199,78) if stars==3 else (210,196,177)
            edge=(255,226,133)
        else:
            fill=(222,145,137) if stars==3 else (197,184,173)
            edge=(175,95,88) if stars==3 else (158,146,135)
        d.rounded_rectangle((x,y,x+tile_w,y+tile_h), radius=12, fill=fill, outline=edge, width=4)
        sign="+" if trophies_delta>0 else ""
        d.text((x+tile_w//2,y+8), f"{sign}{trophies_delta}", font=font(24), fill=(35,30,27), anchor="mt", stroke_width=1, stroke_fill=(255,245,224))
        # Trophy icon approximation
        tx=x+tile_w-17; ty=y+20
        d.ellipse((tx-8,ty-8,tx+8,ty+8), fill=(255,220,55), outline=(112,79,18), width=2)
        for s in range(3):
            sx=x+22+s*30
            if s < stars:
                draw_star(d,sx,y+51,12,(237,250,250))
            else:
                draw_star(d,sx,y+51,12,(145,137,130))
        if destruction is not None:
            d.text((x+tile_w-5,y+tile_h-5), f"{destruction}%", font=font(11), fill=(45,35,30), anchor="rb")
    if not battles:
        d.text((W//2,H//2), "No battle records returned for this day.", font=font(28), fill=(55,45,40), anchor="mm")
    out=io.BytesIO()
    im.save(out,format="PNG")
    out.seek(0)
    return out

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Logged in as {bot.user}; synced {len(synced)} slash commands.")
    except Exception as e:
        print("Slash-command sync failed:", e)

@bot.tree.command(name="legend", description="Create a Legend League battle-log image for a CoC player")
@app_commands.describe(tag="Player tag, e.g. #ABC123", day="Optional Legend League day/date identifier")
async def legend(interaction: discord.Interaction, tag: str, day: str = ""):
    await interaction.response.defer(thinking=True)
    try:
        tag=normalize_tag(tag)
        async with aiohttp.ClientSession(headers={"User-Agent":"CoC-Legend-Discord-Bot/1.0"}) as session:
            player = await fetch_player(session, tag)
            series = await fetch_legend_series(session, tag)
            selected_day=day.strip()
            if not selected_day:
                # Try to infer most recent day from common response shapes.
                candidates=[]
                if isinstance(series, list):
                    candidates=series
                elif isinstance(series, dict):
                    for k in ("items","series","days","data"):
                        if isinstance(series.get(k),list):
                            candidates=series[k]; break
                if candidates:
                    last=candidates[-1]
                    selected_day=str(getv(last,"day","date","seasonDay","id","battleDay",default=""))
                if not selected_day:
                    selected_day=datetime.now().strftime("%Y-%m-%d")
            data=await fetch_legend_battles(session,tag,selected_day)
            battles=extract_battles(data)
            # If the API day key isn't inferred correctly, report that rather than fabricate stats.
            if not battles and not data:
                await interaction.followup.send(
                    f"ما لقيت سجل معارك محفوظ لليوم `{selected_day}` للاعب `{tag}`. "
                    "جرّب تحديد day/date إذا كان عندك، أو تأكد أن اللاعب لديه سجل Legend League محفوظ في ClashKing."
                )
                return
            image=render_image(player or {},tag,selected_day,battles)
            await interaction.followup.send(file=discord.File(image, filename="legend-battle-log.png"))
    except ValueError as e:
        await interaction.followup.send(str(e), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(
            "صار خطأ أثناء جلب السجل أو رسم الصورة. تأكد من الاتصال، ثم راجع سجل التشغيل. "
            f"التفاصيل: `{str(e)[:300]}`", ephemeral=True
        )

if not DISCORD_TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN. Copy .env.example to .env and add your bot token.")
bot.run(DISCORD_TOKEN)
