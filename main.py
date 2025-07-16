import discord
from discord.ext import commands
import requests
import re
import os
import urllib.parse
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def format_exp_value(value: str) -> str:
    """Formata valores de experiência removendo vírgulas e pontos"""
    return value.replace('.', '').replace(',', '')

async def get_tibia_stats(character_name: str):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    encoded_name = urllib.parse.quote(character_name)
    url = f"https://www.guildstats.eu/character?nick={encoded_name}&tab=9"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        content = response.text

        # Extrair Total in month - método robusto
        total_match = re.search(
            r'Total in month.*?([\d\.,]+)',
            content.replace('\n', ' ')
        )
        total_exp = format_exp_value(total_match.group(1)) if total_match else None

        # Extrair dados diários - método preciso
        daily_data = []
        daily_matches = re.finditer(
            r'(?P<date>\d{4}-\d{2}-\d{2}).*?\+(?P<exp>[\d\.,]+)',
            content.replace('\n', ' ')
        )

        # Obter data de ontem no formato YYYY-MM-DD
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        for match in daily_matches:
            if match.group('date') == yesterday:
                daily_data.append({
                    'date': match.group('date'),
                    'exp': format_exp_value(match.group('exp'))
                })
                break  # Encontrou o registro de ontem, pode parar

        if not daily_data:
            # Se não encontrou ontem, pega o último registro disponível
            first_match = re.search(
                r'(\d{4}-\d{2}-\d{2}).*?\+\s*([\d\.,]+)',
                content.replace('\n', ' ')
            )
            if first_match:
                daily_data.append({
                    'date': first_match.group(1),
                    'exp': format_exp_value(first_match.group(2))
                })
            else:
                return {'error': "Nenhum registro diário encontrado"}

        # Ordenar por data (mais recente primeiro)
        daily_data.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'total_month': total_exp,
            'daily_data': daily_data,
            'url': url
        }

    except Exception as e:
        return {'error': f"Erro ao processar dados: {str(e)}"}

@bot.command(name='char')
async def character_info(ctx, *, character_name: str):
    if not character_name.strip():
        await ctx.send("⚠️ Por favor, digite um nome de personagem válido.")
        return
    
    msg = await ctx.send(f"🔍 Analisando {character_name}...")
    stats = await get_tibia_stats(character_name)
    
    if 'error' in stats:
        await msg.edit(content=f"❌ {character_name}: {stats['error']}\n"
                             f"🔗 Verifique manualmente: {stats.get('url', '')}")
    else:
        last_entry = stats['daily_data'][0]
        response = (
            f"**{character_name}**\n"
            f"📅 **Total mensal:** {int(stats['total_month']):,}\n"
            f"🆕 **Última EXP ({last_entry['date']}):** +{int(last_entry['exp']):,}\n"
            f"🔗 [Ver detalhes]({stats['url']})"
        )
        await msg.edit(content=response.replace(',', '.'))

# Configuração do bot
DISCORD_TOKEN = "Token aqui"
if not DISCORD_TOKEN:
    print("❌ ERRO: Token do Discord não configurado!")
    exit(1)

bot.run(DISCORD_TOKEN)