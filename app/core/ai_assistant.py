from anthropic import AsyncAnthropic
from app.core.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)


async def generate_status_update(distance_meters: float, eta_minutes: float | None) -> str:
    eta_text = f"about {eta_minutes:.0f} minutes" if eta_minutes else "an unknown amount of time"

    prompt = (
        f"You are a friendly assistant helping two friends meet up. "
        f"Your friend is currently {distance_meters:.0f} meters away, "
        f"estimated arrival time: {eta_text}. "
        f"Write ONE short, warm, casual sentence (max 20 words) telling the user this update. "
        f"Do not use exclamation marks excessively. Just one natural sentence."
    )

    response = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=60,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()



async def suggest_meeting_spot(lat1: float, lng1: float, lat2: float, lng2: float) -> str:
    mid_lat = (lat1 + lat2) / 2
    mid_lng = (lng1 + lng2) / 2

    prompt = (
        f"Two friends are meeting up. Their approximate midpoint coordinates are "
        f"latitude {mid_lat:.5f}, longitude {mid_lng:.5f} (this is in India). "
        f"In ONE short, casual sentence, suggest they meet somewhere convenient near this midpoint. "
        f"Do not invent specific business names you're not certain exist — speak generally "
        f"(e.g., 'somewhere central near [area]') rather than naming a specific cafe or shop."
    )

    response = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=60,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()