# %%
# %%
#!/usr/bin/env python3

import html
import re
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# ============================================================
# FT RSS FEEDS
# ============================================================

BASE = "https://www.ft.com"

FEEDS = {
    "home": f"{BASE}/rss/home",
    "world": f"{BASE}/world?format=rss",
    "us": f"{BASE}/us?format=rss",
    "uk": f"{BASE}/world-uk?format=rss",
    "europe": f"{BASE}/world/europe?format=rss",
    "asia-pacific": f"{BASE}/world/asia-pacific?format=rss",
    "africa": f"{BASE}/world/africa?format=rss",
    "americas": f"{BASE}/world/americas?format=rss",
    "china": f"{BASE}/china?format=rss",
    "markets": f"{BASE}/markets?format=rss",
    "emerging-markets": f"{BASE}/markets/emerging?format=rss",
    "global-economy": f"{BASE}/global-economy?format=rss",
    "companies": f"{BASE}/companies?format=rss",
    "energy": f"{BASE}/energy?format=rss",
    "financials": f"{BASE}/financials?format=rss",
    "technology": f"{BASE}/technology?format=rss",
    "health": f"{BASE}/health?format=rss",
    "industrials": f"{BASE}/industrials?format=rss",
    "media": f"{BASE}/media?format=rss",
    "professional-services": f"{BASE}/professional-services?format=rss",
    "retail-consumer": f"{BASE}/retail-consumer?format=rss",
    "telecoms": f"{BASE}/telecoms?format=rss",
    "climate-capital": f"{BASE}/climate-capital?format=rss",
    "work-careers": f"{BASE}/work-careers?format=rss",
    "opinion": f"{BASE}/opinion?format=rss",
    "ft-view": f"{BASE}/comment/editorial?format=rss",
    "alphaville": f"{BASE}/alphaville?format=rss",
}


# ============================================================
# SETTINGS
# ============================================================

UK_TZ = ZoneInfo("Europe/London")

today_uk = datetime.now(UK_TZ).date()

HTML_FILE = "FT_today.html"

print()
print(f"Showing FT articles for: {today_uk:%d %B %Y}")


# ============================================================
# CHROME SETUP
# ============================================================

options = Options()

# Comment this out if you want to see Chrome running
options.add_argument("--headless=new")

options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)


# ============================================================
# PARSE DATE
# ============================================================

def parse_date(text):

    if not text:
        return None

    try:

        dt = parsedate_to_datetime(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except (TypeError, ValueError):

        return None


# ============================================================
# GET RSS USING CHROME
# ============================================================

def get_feed(driver, url):

    driver.get(url)

    # No explicit delay
    source = driver.page_source

    # --------------------------------------------------------
    # Try normal RSS XML
    # --------------------------------------------------------

    match = re.search(
        r"(<rss\b.*?</rss>)",
        source,
        flags=re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(1)


    # --------------------------------------------------------
    # Chrome may HTML-escape the XML
    # --------------------------------------------------------

    decoded = html.unescape(source)

    match = re.search(
        r"(<rss\b.*?</rss>)",
        decoded,
        flags=re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(1)


    raise ValueError(
        "Could not find RSS XML in page source"
    )


# ============================================================
# PARSE RSS
# ============================================================

def parse_feed(xml_text):

    root = ET.fromstring(xml_text)

    channel = root.find("channel")

    if channel is None:
        return []

    articles = []

    for item in channel.findall("item"):

        def get(tag):
            return (item.findtext(tag) or "").strip()

        published = parse_date(
            get("pubDate")
        )

        articles.append(
            {
                "published": published,
                "title": get("title"),
                "summary": " ".join(
                    get("description").split()
                ),
                "link": get("link")
            }
        )

    return articles


# ============================================================
# STORAGE / DEDUPLICATION
# ============================================================

seen_links = set()

collected_articles = []

total_articles = 0
total_duplicates = 0


# ============================================================
# COLLECT ARTICLES
# ============================================================

try:

    for section, url in FEEDS.items():

        try:

            # ------------------------------------------------
            # FETCH
            # ------------------------------------------------

            xml_text = get_feed(
                driver,
                url
            )


            # ------------------------------------------------
            # PARSE
            # ------------------------------------------------

            articles = parse_feed(
                xml_text
            )


            # ------------------------------------------------
            # KEEP TODAY'S ARTICLES ONLY
            # London timezone
            # ------------------------------------------------

            articles = [
                article
                for article in articles
                if (
                    article["published"] is not None
                    and
                    article["published"]
                    .astimezone(UK_TZ)
                    .date()
                    == today_uk
                )
            ]


            # ------------------------------------------------
            # SORT NEWEST -> OLDEST WITHIN SECTION
            # ------------------------------------------------

            articles.sort(
                key=lambda x: x["published"],
                reverse=True
            )


            # ------------------------------------------------
            # GLOBAL DEDUPLICATION
            # ------------------------------------------------

            unique_articles = []

            for article in articles:

                link = article["link"].strip()

                # Ignore entries without links
                if not link:
                    continue

                # Ignore if already seen in another section
                if link in seen_links:

                    total_duplicates += 1

                    continue

                seen_links.add(link)

                unique_articles.append(
                    article
                )


            # ------------------------------------------------
            # SKIP EMPTY SECTIONS
            # ------------------------------------------------

            if not unique_articles:
                continue


            # ------------------------------------------------
            # SECTION HEADER
            # ------------------------------------------------

            print()
            print("=" * 100)
            print(section.upper())
            print("=" * 100)


            # ------------------------------------------------
            # PRINT + COLLECT ARTICLES
            # ------------------------------------------------

            for article in unique_articles:

                published_uk = (
                    article["published"]
                    .astimezone(UK_TZ)
                )

                published = published_uk.strftime(
                    "%H:%M"
                )


                # --------------------------------------------
                # PRINT
                # --------------------------------------------

                print()

                print(
                    f"{published} | "
                    f"{section} | "
                    f"{article['title']}"
                )

                if article["summary"]:

                    print(
                        article["summary"]
                    )

                print(
                    article["link"]
                )


                # --------------------------------------------
                # STORE FOR HTML
                # --------------------------------------------

                collected_articles.append(
                    {
                        "published": published,
                        "section": section,
                        "title": article["title"],
                        "summary": article["summary"],
                        "link": article["link"]
                    }
                )

                total_articles += 1


        except Exception as exc:

            print(
                f"[{section}] FAILED: "
                f"{type(exc).__name__}: {exc}"
            )


finally:

    driver.quit()


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)

print(
    f"Date: {today_uk:%d %B %Y}"
)

print(
    f"Unique articles today: {total_articles}"
)

print(
    f"Duplicates removed: {total_duplicates}"
)


# ============================================================
# CREATE HTML
# ============================================================

html_content = f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>
Financial Times - {today_uk:%d %B %Y}
</title>


<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    max-width: 1200px;
    margin: 40px auto;
    padding: 0 25px;
    background-color: #ffffff;
    color: #222222;
}}

h1 {{
    font-size: 30px;
    margin-bottom: 5px;
}}

.date {{
    font-size: 16px;
    color: #666666;
    margin-bottom: 35px;
}}

.article {{
    margin-bottom: 25px;
    padding-bottom: 20px;
    border-bottom: 1px solid #dddddd;
}}

.article-header {{
    font-size: 18px;
    font-weight: bold;
    line-height: 1.4;
    margin-bottom: 8px;
}}

.time {{
    color: #666666;
}}

.section {{
    color: #990f3d;
    text-transform: uppercase;
}}

.title a {{
    color: #222222;
    text-decoration: none;
}}

.title a:hover {{
    color: #990f3d;
    text-decoration: underline;
}}

.summary {{
    font-size: 15px;
    line-height: 1.5;
    color: #444444;
    margin-top: 5px;
}}

</style>

</head>


<body>


<h1>
Financial Times
</h1>


<div class="date">
{today_uk:%A %d %B %Y}
</div>
"""


# ============================================================
# ADD ARTICLES TO HTML
# ============================================================

for article in collected_articles:

    published = html.escape(
        article["published"]
    )

    section = html.escape(
        article["section"]
    )

    title = html.escape(
        article["title"]
    )

    summary = html.escape(
        article["summary"]
    )

    link = html.escape(
        article["link"],
        quote=True
    )


    html_content += f"""

<div class="article">

    <div class="article-header">

        <span class="time">
            {published}
        </span>

        |

        <span class="section">
            {section}
        </span>

        |

        <span class="title">
            <a href="{link}"
               target="_blank"
               rel="noopener noreferrer">
                {title}
            </a>
        </span>

    </div>
"""


    if summary:

        html_content += f"""

    <div class="summary">
        {summary}
    </div>
"""


    html_content += """

</div>
"""


# ============================================================
# CLOSE HTML
# ============================================================

html_content += """

</body>

</html>
"""


# ============================================================
# SAVE HTML
# ============================================================

with open(
    HTML_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(html_content)


print()
print("=" * 100)
print("HTML")
print("=" * 100)

print(
    f"HTML created: {HTML_FILE}"
)

# %%
# %%
#!/usr/bin/env python3

import html
import re
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit, urlunsplit

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# ============================================================
# BLOOMBERG RSS FEEDS
# ============================================================

BASE = "https://www.bloomberg.com"

# Specific feeds are processed first.
# The general news feed is processed last so that duplicated
# stories retain the more specific section name.

FEEDS = {
    "markets": f"{BASE}/feeds/markets/news.rss",
    "economics": f"{BASE}/feeds/economics/news.rss",
    "industries": f"{BASE}/feeds/industries/news.rss",
    "technology": f"{BASE}/feeds/technology/news.rss",
    "politics": f"{BASE}/feeds/politics/news.rss",
    "business": f"{BASE}/feeds/business/news.rss",
    "businessweek": f"{BASE}/feeds/businessweek/news.rss",
    "crypto": f"{BASE}/feeds/crypto/news.rss",
    "news": f"{BASE}/feeds/news.rss",
}


# ============================================================
# SETTINGS
# ============================================================

UK_TZ = ZoneInfo("Europe/London")

today_uk = datetime.now(UK_TZ).date()

HTML_FILE = "Bloomberg_today.html"

print()
print(
    f"Showing Bloomberg articles for: "
    f"{today_uk:%d %B %Y}"
)


# ============================================================
# CHROME SETUP
# ============================================================

options = Options()

# Comment this out if you want to see Chrome running
options.add_argument("--headless=new")

options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if not value:
        return ""

    # Remove any HTML tags from RSS descriptions
    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = html.unescape(value)

    return " ".join(
        value.split()
    )


# ============================================================
# PARSE DATE
# ============================================================

def parse_date(text):

    if not text:
        return None

    text = text.strip()

    # --------------------------------------------------------
    # Standard RSS dates
    # Example:
    # Wed, 21 Oct 2026 09:30:00 GMT
    # --------------------------------------------------------

    try:

        dt = parsedate_to_datetime(text)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt

    except (TypeError, ValueError, OverflowError):
        pass


    # --------------------------------------------------------
    # ISO dates
    # Example:
    # 2026-10-21T09:30:00Z
    # --------------------------------------------------------

    try:

        iso_text = text.replace(
            "Z",
            "+00:00"
        )

        dt = datetime.fromisoformat(
            iso_text
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt

    except (TypeError, ValueError):
        return None


# ============================================================
# NORMALISE URL FOR DEDUPLICATION
# ============================================================

def normalise_link(link):

    if not link:
        return ""

    link = html.unescape(
        link.strip()
    )

    try:

        parts = urlsplit(link)

        # Remove query strings such as:
        # ?srnd=...
        # ?utm_source=...
        #
        # This helps identify the same story appearing with
        # different tracking parameters.

        normalised = urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                "",
                ""
            )
        )

        return normalised

    except ValueError:
        return link


# ============================================================
# REMOVE INVALID XML CHARACTERS
# ============================================================

def remove_invalid_xml_characters(text):

    if not text:
        return ""

    return "".join(
        character
        for character in text
        if (
            character == "\t"
            or character == "\n"
            or character == "\r"
            or ord(character) >= 32
        )
    )


# ============================================================
# EXTRACT XML FROM CHROME PAGE
# ============================================================

def extract_xml(source):

    if not source:
        raise ValueError(
            "Chrome returned an empty page"
        )

    candidates = [
        source,
        html.unescape(source)
    ]

    for candidate in candidates:

        # Try RSS
        match = re.search(
            r"(<rss\b.*?</rss>)",
            candidate,
            flags=re.IGNORECASE | re.DOTALL
        )

        if match:

            xml_text = match.group(1)

            return remove_invalid_xml_characters(
                xml_text
            )


        # Try Atom
        match = re.search(
            r"(<feed\b.*?</feed>)",
            candidate,
            flags=re.IGNORECASE | re.DOTALL
        )

        if match:

            xml_text = match.group(1)

            return remove_invalid_xml_characters(
                xml_text
            )


    raise ValueError(
        "Could not find RSS or Atom XML in the Chrome page"
    )


# ============================================================
# GET FEED USING CHROME
# ============================================================

def get_feed(driver, url):

    driver.get(url)

    # No time.sleep() or other explicit delay
    source = driver.page_source

    try:
        return extract_xml(source)

    except ValueError:

        # Some versions of Chrome place the XML inside a
        # built-in XML viewer. Try the rendered body content
        # as a fallback.

        body_text = driver.execute_script(
            """
            return document.body
                ? document.body.innerText
                : "";
            """
        )

        return extract_xml(
            body_text
        )


# ============================================================
# FIND XML TEXT
# ============================================================

def find_text(element, names):

    for name in names:

        # Direct tag
        child = element.find(name)

        if child is not None and child.text:
            return child.text.strip()


        # Namespace-independent tag
        for candidate in element.iter():

            tag_name = candidate.tag.split(
                "}"
            )[-1].lower()

            if (
                tag_name == name.lower()
                and candidate.text
            ):

                return candidate.text.strip()

    return ""


# ============================================================
# FIND ARTICLE LINK
# ============================================================

def find_link(element):

    # Standard RSS link text
    link = find_text(
        element,
        ["link"]
    )

    if link.startswith("http"):
        return link


    # Atom links usually store the address in href
    for candidate in element.iter():

        tag_name = candidate.tag.split(
            "}"
        )[-1].lower()

        if tag_name != "link":
            continue

        href = candidate.attrib.get(
            "href",
            ""
        ).strip()

        if href:
            return href


    # RSS guid may contain the article URL
    guid = find_text(
        element,
        ["guid", "id"]
    )

    if guid.startswith("http"):
        return guid

    return ""


# ============================================================
# PARSE RSS OR ATOM FEED
# ============================================================

def parse_feed(xml_text):

    root = ET.fromstring(
        xml_text
    )

    root_name = root.tag.split(
        "}"
    )[-1].lower()

    articles = []


    # --------------------------------------------------------
    # RSS
    # --------------------------------------------------------

    if root_name == "rss":

        channel = None

        for element in root:

            if (
                element.tag.split("}")[-1].lower()
                == "channel"
            ):

                channel = element
                break

        if channel is None:
            return []

        entries = [
            element
            for element in channel
            if (
                element.tag.split("}")[-1].lower()
                == "item"
            )
        ]


    # --------------------------------------------------------
    # Atom
    # --------------------------------------------------------

    elif root_name == "feed":

        entries = [
            element
            for element in root
            if (
                element.tag.split("}")[-1].lower()
                == "entry"
            )
        ]


    else:

        entries = [
            element
            for element in root.iter()
            if (
                element.tag.split("}")[-1].lower()
                in {"item", "entry"}
            )
        ]


    # --------------------------------------------------------
    # ARTICLE FIELDS
    # --------------------------------------------------------

    for entry in entries:

        title = clean_text(
            find_text(
                entry,
                ["title"]
            )
        )

        summary = clean_text(
            find_text(
                entry,
                [
                    "description",
                    "summary",
                    "content"
                ]
            )
        )

        published_text = find_text(
            entry,
            [
                "pubDate",
                "published",
                "updated",
                "date"
            ]
        )

        link = find_link(
            entry
        )

        articles.append(
            {
                "published": parse_date(
                    published_text
                ),
                "title": title,
                "summary": summary,
                "link": link
            }
        )

    return articles


# ============================================================
# STORAGE AND GLOBAL DEDUPLICATION
# ============================================================

seen_links = set()

collected_articles = []

failed_feeds = []

total_articles = 0
total_duplicates = 0


# ============================================================
# COLLECT BLOOMBERG ARTICLES
# ============================================================

try:

    for section, url in FEEDS.items():

        try:

            # ------------------------------------------------
            # FETCH
            # ------------------------------------------------

            xml_text = get_feed(
                driver,
                url
            )


            # ------------------------------------------------
            # PARSE
            # ------------------------------------------------

            articles = parse_feed(
                xml_text
            )


            # ------------------------------------------------
            # KEEP TODAY'S ARTICLES ONLY
            # Uses London time rather than UTC
            # ------------------------------------------------

            articles = [
                article
                for article in articles
                if (
                    article["published"] is not None
                    and article["published"]
                    .astimezone(UK_TZ)
                    .date()
                    == today_uk
                )
            ]


            # ------------------------------------------------
            # SORT NEWEST -> OLDEST WITHIN SECTION
            # ------------------------------------------------

            articles.sort(
                key=lambda article: article["published"],
                reverse=True
            )


            # ------------------------------------------------
            # GLOBAL DEDUPLICATION
            # ------------------------------------------------

            unique_articles = []

            for article in articles:

                link = article["link"].strip()

                deduplication_link = normalise_link(
                    link
                )

                # Ignore entries without links
                if not deduplication_link:
                    continue

                # Skip stories already found in another feed
                if deduplication_link in seen_links:

                    total_duplicates += 1

                    continue

                seen_links.add(
                    deduplication_link
                )

                unique_articles.append(
                    article
                )


            # ------------------------------------------------
            # SKIP EMPTY SECTIONS
            # ------------------------------------------------

            if not unique_articles:
                continue


            # ------------------------------------------------
            # SECTION HEADER
            # ------------------------------------------------

            print()
            print("=" * 100)
            print(section.upper())
            print("=" * 100)


            # ------------------------------------------------
            # PRINT AND COLLECT
            # ------------------------------------------------

            for article in unique_articles:

                published_uk = (
                    article["published"]
                    .astimezone(UK_TZ)
                )

                published = published_uk.strftime(
                    "%H:%M"
                )


                # --------------------------------------------
                # PRINT
                # --------------------------------------------

                print()

                print(
                    f"{published} | "
                    f"{section} | "
                    f"{article['title']}"
                )

                if article["summary"]:

                    print(
                        article["summary"]
                    )

                print(
                    article["link"]
                )


                # --------------------------------------------
                # STORE FOR HTML
                # --------------------------------------------

                collected_articles.append(
                    {
                        "published_datetime": published_uk,
                        "published": published,
                        "section": section,
                        "title": article["title"],
                        "summary": article["summary"],
                        "link": article["link"]
                    }
                )

                total_articles += 1


        except Exception as exc:

            failed_feeds.append(
                section
            )

            print(
                f"[{section}] FAILED: "
                f"{type(exc).__name__}: {exc}"
            )


finally:

    driver.quit()


# ============================================================
# SORT FINAL COLLECTION
# Section order first, then newest to oldest
# ============================================================

section_order = {
    section: position
    for position, section in enumerate(FEEDS)
}

collected_articles.sort(
    key=lambda article: (
        section_order.get(
            article["section"],
            len(section_order)
        ),
        -article["published_datetime"].timestamp()
    )
)


# ============================================================
# CONSOLE SUMMARY
# ============================================================

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)

print(
    f"Date: {today_uk:%d %B %Y}"
)

print(
    f"Unique articles today: {total_articles}"
)

print(
    f"Duplicates removed: {total_duplicates}"
)

if failed_feeds:

    print(
        "Failed feeds: "
        + ", ".join(failed_feeds)
    )


# ============================================================
# CREATE HTML
# ============================================================

html_content = f"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Bloomberg - {today_uk:%d %B %Y}</title>

<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    max-width: 1200px;
    margin: 40px auto;
    padding: 0 25px;
    background-color: #ffffff;
    color: #222222;
}}

h1 {{
    font-size: 30px;
    margin-bottom: 5px;
}}

.date {{
    font-size: 16px;
    color: #666666;
    margin-bottom: 35px;
}}

.section-heading {{
    margin-top: 36px;
    padding-bottom: 8px;
    border-bottom: 3px solid #000000;
    font-size: 22px;
    text-transform: uppercase;
}}

.article {{
    margin-bottom: 25px;
    padding: 18px 0 20px 0;
    border-bottom: 1px solid #dddddd;
}}

.article-header {{
    font-size: 18px;
    font-weight: bold;
    line-height: 1.4;
    margin-bottom: 8px;
}}

.time {{
    color: #666666;
}}

.section {{
    color: #5b36f2;
    text-transform: uppercase;
}}

.title a {{
    color: #222222;
    text-decoration: none;
}}

.title a:hover {{
    color: #5b36f2;
    text-decoration: underline;
}}

.summary {{
    font-size: 15px;
    line-height: 1.5;
    color: #444444;
    margin-top: 5px;
}}

.empty-message {{
    color: #666666;
    font-style: italic;
}}

</style>

</head>

<body>

<h1>Bloomberg</h1>

<div class="date">
    {today_uk:%A %d %B %Y}
</div>
"""


# ============================================================
# ADD ARTICLES TO HTML
# ============================================================

if not collected_articles:

    html_content += """

<div class="empty-message">
    No articles dated today were found.
</div>
"""

else:

    current_section = None

    for article in collected_articles:

        published = html.escape(
            article["published"]
        )

        section = html.escape(
            article["section"]
        )

        title = html.escape(
            article["title"]
        )

        summary = html.escape(
            article["summary"]
        )

        link = html.escape(
            article["link"],
            quote=True
        )


        # ----------------------------------------------------
        # SECTION HEADING
        # ----------------------------------------------------

        if article["section"] != current_section:

            current_section = article["section"]

            html_content += f"""

<h2 class="section-heading">
    {section}
</h2>
"""


        # ----------------------------------------------------
        # ARTICLE
        # ----------------------------------------------------

        html_content += f"""

<div class="article">

    <div class="article-header">

        <span class="time">
            {published}
        </span>

        |

        <span class="section">
            {section}
        </span>

        |

        <span class="title">
            <a href="{link}"
               target="_blank"
               rel="noopener noreferrer">
                {title}
            </a>
        </span>

    </div>
"""


        if summary:

            html_content += f"""

    <div class="summary">
        {summary}
    </div>
"""


        html_content += """

</div>
"""


# ============================================================
# CLOSE HTML
# ============================================================

html_content += """

</body>
</html>
"""


# ============================================================
# SAVE HTML
# ============================================================

with open(
    HTML_FILE,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        html_content
    )


print()
print("=" * 100)
print("HTML")
print("=" * 100)

print(
    f"HTML created: {HTML_FILE}"
)

# %%
# %%
#!/usr/bin/env python3

import html
import re
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# ============================================================
# ECONOMIST RSS FEEDS
# ============================================================
# Pattern: https://www.economist.com/<section>/rss.xml
#
# Order matters because of global de-duplication: an article is
# credited to the FIRST feed it appears in. Specific sections come
# first and the catch-all "latest" feed comes last, so "latest" only
# shows articles that no section feed already covered.
#
# Feeds confirmed working (Feeder, checked 3 Oct 2026):
#   latest, finance-and-economics, business, united-states,
#   the-americas, britain, international, europe, asia, letters,
#   podcasts, erasmus, gulliver, obituary
# The others below follow the same URL pattern but were not
# individually confirmed. Any that fail just print FAILED and the
# script carries on.

BASE = "https://www.economist.com"

SECTIONS = [
    "leaders",
    "briefing",
    "the-world-this-week",
    "united-states",
    "the-americas",
    "asia",
    "china",
    "middle-east-and-africa",
    "europe",
    "britain",
    "international",
    "business",
    "finance-and-economics",
    "science-and-technology",
    "culture",
    "graphic-detail",
    "by-invitation",
    "letters",
    "obituary",
    "podcasts",
    "latest",
]

FEEDS = {name: f"{BASE}/{name}/rss.xml" for name in SECTIONS}


# ============================================================
# SETTINGS
# ============================================================

UK_TZ = ZoneInfo("Europe/London")

today_uk = datetime.now(UK_TZ).date()

# 0 = today only. Set to 1 to include yesterday as well, etc.
# The Economist publishes far fewer pieces per day than the FT,
# so you may want 1 or 2.
DAYS_BACK = 0

earliest_date = today_uk - timedelta(days=DAYS_BACK)

HTML_FILE = "Economist_today.html"

print()
if DAYS_BACK == 0:
    print(f"Showing Economist articles for: {today_uk:%d %B %Y}")
else:
    print(
        f"Showing Economist articles from: "
        f"{earliest_date:%d %B %Y} to {today_uk:%d %B %Y}"
    )


# ============================================================
# CHROME SETUP
# ============================================================

options = Options()

# Comment this out if you want to see Chrome running
options.add_argument("--headless=new")

options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)


# ============================================================
# PARSE DATE
# ============================================================

def parse_date(text):

    if not text:
        return None

    # RFC 822 style (standard RSS)
    try:

        dt = parsedate_to_datetime(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except (TypeError, ValueError):
        pass

    # ISO 8601 fallback
    try:

        dt = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except ValueError:

        return None


# ============================================================
# CLEAN HELPERS
# ============================================================

def strip_tags(text):

    text = re.sub(r"<[^>]+>", " ", text)

    text = html.unescape(text)

    return " ".join(text.split())


def normalise_link(link):

    # Drop tracking query strings / fragments so the same article
    # is recognised across feeds
    parts = urlsplit(link.strip())

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, "", "")
    )


# ============================================================
# GET RSS USING CHROME
# ============================================================

def get_feed(driver, url):

    driver.get(url)

    # No explicit delay
    source = driver.page_source

    # --------------------------------------------------------
    # Try normal RSS XML
    # --------------------------------------------------------

    match = re.search(
        r"(<rss\b.*?</rss>)",
        source,
        flags=re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(1)


    # --------------------------------------------------------
    # Chrome may HTML-escape the XML
    # --------------------------------------------------------

    decoded = html.unescape(source)

    match = re.search(
        r"(<rss\b.*?</rss>)",
        decoded,
        flags=re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(1)


    raise ValueError(
        "Could not find RSS XML in page source"
    )


# ============================================================
# PARSE RSS
# ============================================================

def parse_feed(xml_text):

    root = ET.fromstring(xml_text)

    channel = root.find("channel")

    if channel is None:
        return []

    articles = []

    for item in channel.findall("item"):

        def get(tag):
            return (item.findtext(tag) or "").strip()

        published = parse_date(
            get("pubDate")
        )

        articles.append(
            {
                "published": published,
                "title": strip_tags(get("title")),
                "summary": strip_tags(
                    get("description")
                ),
                "link": get("link")
            }
        )

    return articles


# ============================================================
# STORAGE / DEDUPLICATION
# ============================================================

seen_links = set()

collected_articles = []

total_articles = 0
total_duplicates = 0


# ============================================================
# COLLECT ARTICLES
# ============================================================

try:

    for section, url in FEEDS.items():

        try:

            # ------------------------------------------------
            # FETCH
            # ------------------------------------------------

            xml_text = get_feed(
                driver,
                url
            )


            # ------------------------------------------------
            # PARSE
            # ------------------------------------------------

            articles = parse_feed(
                xml_text
            )


            # ------------------------------------------------
            # KEEP RECENT ARTICLES ONLY
            # London timezone
            # ------------------------------------------------

            articles = [
                article
                for article in articles
                if (
                    article["published"] is not None
                    and
                    earliest_date
                    <= article["published"]
                    .astimezone(UK_TZ)
                    .date()
                    <= today_uk
                )
            ]


            # ------------------------------------------------
            # SORT NEWEST -> OLDEST WITHIN SECTION
            # ------------------------------------------------

            articles.sort(
                key=lambda x: x["published"],
                reverse=True
            )


            # ------------------------------------------------
            # GLOBAL DEDUPLICATION
            # ------------------------------------------------

            unique_articles = []

            for article in articles:

                raw_link = article["link"].strip()

                # Ignore entries without links
                if not raw_link:
                    continue

                key = normalise_link(raw_link)

                # Ignore if already seen in another section
                if key in seen_links:

                    total_duplicates += 1

                    continue

                seen_links.add(key)

                unique_articles.append(
                    article
                )


            # ------------------------------------------------
            # SKIP EMPTY SECTIONS
            # ------------------------------------------------

            if not unique_articles:
                continue


            # ------------------------------------------------
            # SECTION HEADER
            # ------------------------------------------------

            print()
            print("=" * 100)
            print(section.upper())
            print("=" * 100)


            # ------------------------------------------------
            # PRINT + COLLECT ARTICLES
            # ------------------------------------------------

            for article in unique_articles:

                published_uk = (
                    article["published"]
                    .astimezone(UK_TZ)
                )

                # Include the date when looking back more than today
                if DAYS_BACK == 0:
                    published = published_uk.strftime(
                        "%H:%M"
                    )
                else:
                    published = published_uk.strftime(
                        "%d %b %H:%M"
                    )


                # --------------------------------------------
                # PRINT
                # --------------------------------------------

                print()

                print(
                    f"{published} | "
                    f"{section} | "
                    f"{article['title']}"
                )

                if article["summary"]:

                    print(
                        article["summary"]
                    )

                print(
                    article["link"]
                )


                # --------------------------------------------
                # STORE FOR HTML
                # --------------------------------------------

                collected_articles.append(
                    {
                        "published": published,
                        "section": section,
                        "title": article["title"],
                        "summary": article["summary"],
                        "link": article["link"]
                    }
                )

                total_articles += 1


        except Exception as exc:

            print(
                f"[{section}] FAILED: "
                f"{type(exc).__name__}: {exc}"
            )


finally:

    driver.quit()


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)

print(
    f"Date: {today_uk:%d %B %Y}"
)

print(
    f"Unique articles: {total_articles}"
)

print(
    f"Duplicates removed: {total_duplicates}"
)


# ============================================================
# CREATE HTML
# ============================================================

html_content = f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>
The Economist - {today_uk:%d %B %Y}
</title>


<style>

body {{
    font-family: Arial, Helvetica, sans-serif;
    max-width: 1200px;
    margin: 40px auto;
    padding: 0 25px;
    background-color: #ffffff;
    color: #222222;
}}

h1 {{
    font-size: 30px;
    margin-bottom: 5px;
    border-top: 6px solid #e3120b;
    padding-top: 12px;
}}

.date {{
    font-size: 16px;
    color: #666666;
    margin-bottom: 35px;
}}

.article {{
    margin-bottom: 25px;
    padding-bottom: 20px;
    border-bottom: 1px solid #dddddd;
}}

.article-header {{
    font-size: 18px;
    font-weight: bold;
    line-height: 1.4;
    margin-bottom: 8px;
}}

.time {{
    color: #666666;
}}

.section {{
    color: #e3120b;
    text-transform: uppercase;
}}

.title a {{
    color: #222222;
    text-decoration: none;
}}

.title a:hover {{
    color: #e3120b;
    text-decoration: underline;
}}

.summary {{
    font-size: 15px;
    line-height: 1.5;
    color: #444444;
    margin-top: 5px;
}}

</style>

</head>


<body>


<h1>
The Economist
</h1>


<div class="date">
{today_uk:%A %d %B %Y}
</div>
"""


# ============================================================
# ADD ARTICLES TO HTML
# ============================================================

for article in collected_articles:

    published = html.escape(
        article["published"]
    )

    section = html.escape(
        article["section"]
    )

    title = html.escape(
        article["title"]
    )

    summary = html.escape(
        article["summary"]
    )

    link = html.escape(
        article["link"],
        quote=True
    )


    html_content += f"""

<div class="article">

    <div class="article-header">

        <span class="time">
            {published}
        </span>

        |

        <span class="section">
            {section}
        </span>

        |

        <span class="title">
            <a href="{link}"
               target="_blank"
               rel="noopener noreferrer">
                {title}
            </a>
        </span>

    </div>
"""


    if summary:

        html_content += f"""

    <div class="summary">
        {summary}
    </div>
"""


    html_content += """

</div>
"""


# ============================================================
# CLOSE HTML
# ============================================================

html_content += """

</body>

</html>
"""


# ============================================================
# SAVE HTML
# ============================================================

with open(
    HTML_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(html_content)


print()
print("=" * 100)
print("HTML")
print("=" * 100)

print(
    f"HTML created: {HTML_FILE}"
)


