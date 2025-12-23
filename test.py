
import asyncio
from app.services.ai_assistant import generate_ai_summary
async def main():
    out = await generate_ai_summary("发热两天，咽痛，伴干咳，无胸闷气短")
    print("AI输出:", out)
asyncio.run(main())
