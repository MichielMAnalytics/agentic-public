import asyncio
import datetime
from telethon import TelegramClient
import os
from dotenv import load_dotenv

#load environment vars
load_dotenv() 

TG_API_ID= os.environ.get("TG_API_ID") 
TG_API_HASH=os.environ.get("TG_API_HASH") 
phone_number=os.environ.get("PHONE_NUMBER") 

async def main():
    client = TelegramClient('anon', TG_API_ID, TG_API_HASH)

    await client.start(phone_number)
    print("Client started and connected.")

    await client.disconnect()
    print("Client disconnected.")

if __name__ == "__main__":
    asyncio.run(main())