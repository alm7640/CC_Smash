# merchant_map.py
# Normalizes raw merchant strings to clean display names
# Format: "fragment_to_match_lowercase": "Clean Name"

MERCHANT_ALIASES = {
    # Amazon
    "amzn": "Amazon",
    "amazon": "Amazon",
    "amz*": "Amazon",
    # Streaming
    "netflix": "Netflix",
    "nflx": "Netflix",
    "spotify": "Spotify",
    "hulu": "Hulu",
    "disney": "Disney+",
    "disneyplus": "Disney+",
    "hbo": "HBO Max",
    "max.com": "HBO Max",
    "peacock": "Peacock",
    "paramount": "Paramount+",
    "appletv": "Apple TV+",
    "apple.com/bill": "Apple Services",
    "apple services": "Apple Services",
    "itunes": "Apple Services",
    "youtube": "YouTube Premium",
    "youtubepremium": "YouTube Premium",
    # Food delivery
    "doordash": "DoorDash",
    "ubereats": "Uber Eats",
    "grubhub": "Grubhub",
    "seamless": "Seamless",
    "instacart": "Instacart",
    # Rideshare
    "uber": "Uber",
    "lyft": "Lyft",
    # Grocery
    "wholefds": "Whole Foods",
    "whole foods": "Whole Foods",
    "trader joe": "Trader Joe's",
    "kroger": "Kroger",
    "safeway": "Safeway",
    "wegmans": "Wegmans",
    "shoprite": "ShopRite",
    "costco": "Costco",
    "sams club": "Sam's Club",
    "target": "Target",
    "walmart": "Walmart",
    # Fuel
    "shell": "Shell",
    "exxon": "ExxonMobil",
    "mobil": "ExxonMobil",
    "bp ": "BP",
    "chevron": "Chevron",
    "sunoco": "Sunoco",
    "wawa": "Wawa",
    "quick chek": "Quick Chek",
    "quickchek": "Quick Chek",
    # Coffee
    "starbucks": "Starbucks",
    "dunkin": "Dunkin'",
    "dutch bros": "Dutch Bros",
    "caribou": "Caribou Coffee",
    # Fast food
    "mcdonald": "McDonald's",
    "mcdonalds": "McDonald's",
    "chick-fil-a": "Chick-fil-A",
    "chickfila": "Chick-fil-A",
    "chipotle": "Chipotle",
    "taco bell": "Taco Bell",
    "tacobell": "Taco Bell",
    "burger king": "Burger King",
    "burgerking": "Burger King",
    "wendy": "Wendy's",
    "subway": "Subway",
    "panera": "Panera Bread",
    # Tech / Cloud
    "google": "Google",
    "microsoft": "Microsoft",
    "msft": "Microsoft",
    "adobe": "Adobe",
    "dropbox": "Dropbox",
    "github": "GitHub",
    "openai": "OpenAI",
    "chatgpt": "OpenAI",
    "zoom": "Zoom",
    "slack": "Slack",
    "notion": "Notion",
    "1password": "1Password",
    "lastpass": "LastPass",
    # Fitness
    "planet fitness": "Planet Fitness",
    "la fitness": "LA Fitness",
    "lafitness": "LA Fitness",
    "peloton": "Peloton",
    "equinox": "Equinox",
    "anytime fitness": "Anytime Fitness",
    "ymca": "YMCA",
    # Insurance
    "geico": "GEICO",
    "progressive": "Progressive",
    "statefarm": "State Farm",
    "state farm": "State Farm",
    "allstate": "Allstate",
    # Utilities/Telecom
    "verizon": "Verizon",
    "at&t": "AT&T",
    "att ": "AT&T",
    "t-mobile": "T-Mobile",
    "tmobile": "T-Mobile",
    "comcast": "Comcast/Xfinity",
    "xfinity": "Comcast/Xfinity",
    "spectrum": "Spectrum",
    # Shopping
    "etsy": "Etsy",
    "ebay": "eBay",
    "bestbuy": "Best Buy",
    "best buy": "Best Buy",
    "home depot": "Home Depot",
    "homedepot": "Home Depot",
    "lowes": "Lowe's",
    "wayfair": "Wayfair",
    "chewy": "Chewy",
    # Travel
    "airbnb": "Airbnb",
    "vrbo": "VRBO",
    "expedia": "Expedia",
    "hotels.com": "Hotels.com",
    "booking.com": "Booking.com",
    "united air": "United Airlines",
    "delta air": "Delta Airlines",
    "american air": "American Airlines",
    "southwest": "Southwest Airlines",
    "jetblue": "JetBlue",
}


def normalize_merchant(raw: str) -> str:
    """
    Attempt to normalize a raw merchant string to a clean name.
    Returns the best match or a cleaned version of the original.
    """
    if not raw:
        return "Unknown"
    cleaned = raw.strip().lower()
    # Remove common noise suffixes
    for noise in ["*", "#", "  "]:
        cleaned = cleaned.replace(noise, " ")
    cleaned = cleaned.strip()

    for fragment, clean_name in MERCHANT_ALIASES.items():
        if fragment in cleaned:
            return clean_name

    # Fallback: title-case the raw string, trim long codes
    words = raw.strip().split()
    # Drop trailing tokens that look like reference codes (all digits/caps short tokens)
    filtered = []
    for w in words:
        if len(w) <= 3 and w.isupper() and w.isalpha():
            continue  # likely a state abbreviation or noise
        if w.isdigit():
            continue
        filtered.append(w)
    return " ".join(filtered[:4]).title() if filtered else raw.title()
