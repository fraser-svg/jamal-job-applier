import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "jobs.db"
CV_PATH = DATA_DIR / "cv.pdf"
PROFILE_PATH = DATA_DIR / "profile.json"

# Load Jamal's profile
try:
    with open(PROFILE_PATH) as f:
        PROFILE = json.load(f)
except FileNotFoundError:
    print(f"ERROR: Profile not found at {PROFILE_PATH}")
    print("Copy data/profile.json.example to data/profile.json and fill in details.")
    sys.exit(1)

# Email config
APP_EMAIL = os.getenv("APP_EMAIL")
APP_EMAIL_PASSWORD = os.getenv("APP_EMAIL_PASSWORD")
JAMAL_EMAIL = os.getenv("JAMAL_EMAIL")

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Search parameters
SEARCH_LOCATION = "Glasgow"
SEARCH_KEYWORDS = [
    "kitchen porter",
    "kitchen assistant",
    "commis chef",
    "catering assistant",
    "dishwasher",
    "hospitality assistant",
    "food service assistant",
    "waiting staff",
]
MAX_HOURS = 16

# Rate limiting
DETAIL_PAGE_DELAY_MS = 2000
MAX_DETAIL_PAGES_PER_SCRAPER = 25

# Glasgow city centre and nearby postcodes
VALID_AREAS = [
    "glasgow", "city centre", "garnethill", "merchant city",
    "finnieston", "charing cross", "cowcaddens", "anderston",
    "tradeston", "townhead", "dennistoun", "partick",
    "hillhead", "kelvinbridge", "st george's cross",
    "buchanan", "argyle", "sauchiehall", "byres road",
    "west end", "g1", "g2", "g3", "g4", "g11", "g12", "g20",
]

# Areas that are too far
EXCLUDED_AREAS = [
    "east kilbride", "hamilton", "motherwell", "paisley",
    "cumbernauld", "coatbridge", "airdrie", "dumbarton",
    "greenock", "kilmarnock", "stirling",
]
