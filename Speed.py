import os
import aiohttp
import asyncio
import time
import random

# === Settings ===

WEBHOOK_URL = "https://discord.com/api/webhooks/1373286687668699187/AS1PLzkeCJNyDlP5Lrf4jqZHfWX1ie2g786lRisf19iXqg0G1loBH8Yh_CKt9YXNSoER"
INPUT_FILE = "testsada.txt"
BATCH_SIZE = 20
MAX_CONCURRENT_REQUESTS = 10

# === Headers rotation data ===

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
]

ACCEPT_LANGUAGES = [
    "sk-SK,sk;q=0.9,cs;q=0.8,en-US;q=0.7,en;q=0.6",
    "en-US,en;q=0.9",
    "en-GB,en;q=0.8",
]

SEC_CH_UA_VALUES = [
    '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    '"Google Chrome";v="136", "Chromium";v="136", "Not/A)Brand";v="24"',
    '"Google Chrome";v="135", "Chromium";v="135", "Not/A)Brand";v="24"',
]

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Ch-Ua": random.choice(SEC_CH_UA_VALUES),
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

# === Read usernames from file ===

def read_usernames_from_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    random.shuffle(lines)  # Shuffle entire file each time read
    return lines

# === Get public IP ===

async def get_public_ip(session):
    try:
        async with session.get("https://api.ipify.org", timeout=10, headers=get_random_headers()) as resp:
            return await resp.text()
    except Exception:
        return "unknown"

# === Batch check usernames ===

async def check_batch_usernames(session, usernames_batch):
    joined_names = ",".join(usernames_batch)
    url = f"https://api-cops.criticalforce.fi/api/public/profile?usernames={joined_names}"
    try:
        ip = await get_public_ip(session)
        print(f"🌐 Batch ({len(usernames_batch)}): Sending from IP {ip}")
        async with session.get(url, timeout=30, headers=get_random_headers()) as response:
            print(f"➡️  Response: {response.status}")
            return response.status == 500
    except Exception as e:
        print(f"Batch error: {e}")
        return False

# === Check individual username ===

async def check_username_individually(session, username):
    url = f"https://api-cops.criticalforce.fi/api/public/profile?usernames={username}"
    try:
        async with session.get(url, timeout=30, headers=get_random_headers()) as response:
            print(f"🔍 {username}: {response.status}")
            return username if response.status == 500 else None
    except Exception as e:
        print(f"❌ {username} failed: {e}")
        return None

# === Recursive divide & conquer ===

async def divide_and_conquer(usernames, session):
    if len(usernames) == 1:
        result = await check_username_individually(session, usernames[0])
        return [result] if result else []

    if await check_batch_usernames(session, usernames):
        mid = len(usernames) // 2
        left = await divide_and_conquer(usernames[:mid], session)
        right = await divide_and_conquer(usernames[mid:], session)
        return left + right
    return []

# === Send Discord webhook (per batch) ===

async def send_discord_notification(free_names, batch_number):
    if not free_names or not WEBHOOK_URL:
        return
    message = f"**🚨 Free Usernames Found (Batch {batch_number})!**\n" + "\n".join(f"- {name}" for name in free_names)
    payload = {"content": message}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(WEBHOOK_URL, json=payload, headers=get_random_headers()) as resp:
                if resp.status in (200, 204):
                    print(f"✅ Discord: Batch {batch_number} sent.")
                else:
                    print(f"❌ Discord Error: {resp.status}")
        except Exception as e:
            print(f"❌ Discord Exception: {e}")

# === Send final summary ===

import datetime  # Add this at the top of your file

# === Send final summary ===

async def send_summary_notification(free_names, duration):
    if not free_names or not WEBHOOK_URL:
        return
    duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Real current time
    message = (
        f"**📊 IGN Check Summary**\n"
        f"🕒 Time: `{duration_str}`\n"
        f"📅 Date: `{current_time}`\n"
        f"🟩 Total Free: `{len(free_names)}`\n\n"
        f"**List:**\n" + "\n".join(f"- {name}" for name in free_names)
    )
    payload = {"content": message}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(WEBHOOK_URL, json=payload, headers=get_random_headers()) as resp:
                if resp.status in (200, 204):
                    print("✅ Summary sent.")
                else:
                    print(f"❌ Summary error: {resp.status}")
        except Exception as e:
            print(f"❌ Summary exception: {e}")

# === Process single batch ===

async def process_batch(batch_num, batch, free_names, session):
    # Shuffle usernames inside batch for each check to randomize order
    random.shuffle(batch)
    print(f"\n🔍 Batch {batch_num}: {len(batch)} usernames")
    if await check_batch_usernames(session, batch):
        print(f"✅ Batch {batch_num} = 500. Starting deep check.")
        confirmed = await divide_and_conquer(batch, session)
        if confirmed:
            free_names.extend(confirmed)
            await send_discord_notification(confirmed, batch_num)
    else:
        print(f"❌ Batch {batch_num} = taken.")

# === Main loop ===

async def main_loop():
    while True:
        all_usernames = read_usernames_from_file(INPUT_FILE)
        if not all_usernames:
            print("📁 No usernames found. Sleeping 30s...")
            await asyncio.sleep(30)
            continue

        total = len(all_usernames)
        free_names = []
        start_time = time.time()

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)) as session:
            tasks = []
            for batch_num, i in enumerate(range(0, total, BATCH_SIZE), start=1):
                batch = all_usernames[i:i+BATCH_SIZE]
                tasks.append(process_batch(batch_num, batch, free_names, session))
            await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        print("\n=== ✅ Loop Summary ===")
        print(f"🟩 Free: {len(free_names)}")
        print(f"📝 {free_names}")
        print(f"⏱️ Duration: {time.strftime('%H:%M:%S', time.gmtime(duration))}")
        print("🔁 Restarting in 60s...\n")

        await send_summary_notification(free_names, duration)
        await asyncio.sleep(130)

# === Entry Point ===

if __name__ == "__main__":
    asyncio.run(main_loop())

