import discord
from discord import app_commands
from discord.ext import commands
import vlc
import asyncio
import os
from dotenv import load_dotenv
from m3u_ipytv import playlist

# 載入 .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ 錯誤：找不到 DISCORD_TOKEN")
    exit()

# ================== 自動從 iptv-org 載入台灣頻道 ==================
M3U_URL = "https://iptv-org.github.io/iptv/countries/tw.m3u"

print("🔄 正在從 iptv-org 載入台灣頻道清單...")
pl = playlist.loadu(M3U_URL)   # 從網址載入

# 轉成我們原本的格式（只取 name 和 url）
tv_channels = []
for i, channel in enumerate(pl, start=1):
    name = channel.name.strip()
    url = channel.url.strip()
    if url:  # 只加入有網址的
        tv_channels.append({
            "num": i,
            "name": name,
            "url": url
        })

print(f"✅ 成功載入 {len(tv_channels)} 個台灣頻道！")

# ================== 機器人設定（其餘部分不變）==================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

player = None
current_index = 0

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ {bot.user} 已上線！共載入 {len(tv_channels)} 個頻道")

# ================== Slash 指令（維持原本）==================
@tree.command(name="轉台", description="切換到指定的電視頻道")
@app_commands.describe(channel="頻道號碼 或 頻道名稱")
async def change_channel(interaction: discord.Interaction, channel: str):
    global player, current_index
    if player is None:
        player = vlc.MediaPlayer()

    for i, ch in enumerate(tv_channels):
        if str(ch["num"]) == channel or ch["name"].lower() in channel.lower():
            current_index = i
            media = vlc.Media(ch["url"])
            player.set_media(media)
            player.play()
            await interaction.response.send_message(
                f"📺 已切換到 **第 {ch['num']} 台 - {ch['name']}**"
            )
            return

    await interaction.response.send_message(f"❌ 找不到「{channel}」", ephemeral=True)

@tree.command(name="下一台", description="下一個頻道")
async def next_channel(interaction: discord.Interaction):
    global current_index
    if not tv_channels:
        await interaction.response.send_message("❌ 清單是空的", ephemeral=True)
        return
    current_index = (current_index + 1) % len(tv_channels)
    ch = tv_channels[current_index]
    await change_channel(interaction, str(ch["num"]))

@tree.command(name="上一台", description="上一個頻道")
async def prev_channel(interaction: discord.Interaction):
    global current_index
    if not tv_channels:
        await interaction.response.send_message("❌ 清單是空的", ephemeral=True)
        return
    current_index = (current_index - 1) % len(tv_channels)
    ch = tv_channels[current_index]
    await change_channel(interaction, str(ch["num"]))

@tree.command(name="頻道列表", description="顯示所有可用頻道（前 30 個）")
async def list_channels(interaction: discord.Interaction):
    if not tv_channels:
        await interaction.response.send_message("❌ 沒有頻道", ephemeral=True)
        return

    msg = f"📺 **台灣第四台頻道列表**（共 {len(tv_channels)} 台）\n"
    for ch in tv_channels[:30]:   # 只顯示前30個，避免訊息太長
        msg += f"`{ch['num']}` {ch['name']}\n"
    if len(tv_channels) > 30:
        msg += f"\n... 還有 {len(tv_channels)-30} 台未顯示"
    await interaction.response.send_message(msg)

@tree.command(name="停止", description="停止播放")
async def stop_tv(interaction: discord.Interaction):
    global player
    if player:
        player.stop()
        await interaction.response.send_message("⏹️ 已停止")
    else:
        await interaction.response.send_message("目前沒有播放")

# 啟動
if __name__ == "__main__":
    bot.run(TOKEN)
