import feedparser, datetime, os, requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dateutil import parser as dateparser

SENSATIONAL = ["exposed","destroyed","shocking","insane","collapse","apocalypse","secret","they don't want you to know","ultimate","never seen","breaking","must see","bombshell","meltdown","obliterates","epic","unbelievable"]
LOADED = ["idiot","thug","degenerate","terrorist","traitor","groomer","commie","fascist","lunatic","clown","cuck","sheeple"]
US_VS_THEM_TERMS = ["they","them","these people","the elites","mainstream media","the woke","libs","conservatives","globalists"]
CLICKBAIT_CUES = ["you won't believe","shocking","what happens next","exposed","insane","secret"]
APPEAL_AUTHORITY = ["experts say","scientists agree","data proves","study shows","according to sources"]
APPEAL_COMMONSENSE = ["obviously","anyone can see","it’s common sense","clearly"]
APPEAL_EMOTION = ["outrage","fear","terrified","heartbreaking","disgusting","proud","hope"]
ANECDOTE_TREND = ["everyone is","people are saying","goes viral","trend proves"]

AFFILIATION_KEYWORDS = ["NRA","Turning Point USA","PragerU","Daily Wire","Blaze Media","Heritage Foundation","Project Veritas","Moms for Liberty","GOP","RNC","DNC","Antifa","Black Lives Matter","Proud Boys","Oath Keepers","Sierra Club","ACLU","Human Rights Campaign","NARAL","Susan B. Anthony List","ALEC"]
IDEOLOGY_KEYWORDS = ["libertarian","socialist","marxist","communist","anarchist","conservative","progressive","nationalist","populist","christian nationalist","theocratic","secular","feminist","traditionalist"]

def parse_generic_rss(rss_url, limit=30):
    d = feedparser.parse(rss_url)
    items = []
    for e in d.entries[:limit]:
        title = e.get("title","").strip()
        link = e.get("link","")
        published = e.get("published","") or e.get("updated","") or ""
        try:
            dt = dateparser.parse(published).date().isoformat() if published else ""
        except Exception:
            dt = ""
        summary = Beautifulsoup_safe(e.get("summary", ""))
        items.append({"date": dt, "title": title, "url": link,
                      "platform": urlparse(rss_url).netloc, "description": summary})
    return items

def Beautifulsoup_safe(html):
    try:
        return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    except Exception:
        return ""

def yt_channel_id_from_url(url: str) -> str:
    parts = urlparse(url)
    segs = [s for s in parts.path.split("/") if s]
    if len(segs)>=2 and segs[0].lower()=="channel":
        return segs[1]
    return ""

def yt_rss_from_channel_id(cid: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"

def analyze_text(text: str):
    t = (text or "").lower()
    sensational_hits = [w for w in SENSATIONAL if w in t]
    loaded_hits = [w for w in LOADED if w in t]
    us_them = any(w in t for w in US_VS_THEM_TERMS)
    explicit = any(x in t for x in ["f**","f*ck","fuck","shit","bitch","asshole"])
    clickbait = any(w in t for w in CLICKBAIT_CUES)
    appeal_auth = any(w in t for w in APPEAL_AUTHORITY)
    appeal_common = any(w in t for w in APPEAL_COMMONSENSE)
    appeal_emotion = any(w in t for w in APPEAL_EMOTION)
    anecdote = any(w in t for w in ANECDOTE_TREND)
    affiliations = [w for w in AFFILIATION_KEYWORDS if w.lower() in t]
    ideologies = [w for w in IDEOLOGY_KEYWORDS if w in t]
    return {
        "sensational_terms": ", ".join(sensational_hits),
        "loaded_terms": ", ".join(loaded_hits),
        "us_vs_them": us_them,
        "explicit_language": explicit,
        "clickbait": clickbait,
        "appeal_authority": appeal_auth,
        "appeal_common_sense": appeal_common,
        "appeal_emotion": appeal_emotion,
        "anecdote_as_trend": anecdote,
        "affiliations_found": ", ".join(sorted(set(affiliations))),
        "ideology_hits": ", ".join(sorted(set(ideologies)))
    }

def monetization_signals(text: str):
    t = (text or "").lower()
    hits = []
    if any(k in t for k in ["sponsor","sponsored by","paid partnership"]): hits.append("sponsor")
    if any(k in t for k in ["promo code","use code","my code"]): hits.append("promo code")
    if any(k in t for k in ["affiliate","ref link","referral"]): hits.append("affiliate")
    if any(k in t for k in ["patreon","substack","buymeacoffee","locals.com","membership"]): hits.append("donations/membership")
    if any(k in t for k in ["merch","store","shop","teespring"]): hits.append("merch")
    return ", ".join(sorted(set(hits)))

def build_chicago_note(url: str, title: str, access_date: str):
    host = urlparse(url).netloc
    return f"{title}. {host}. Accessed {access_date}. {url}"

def today_iso(): return datetime.date.today().isoformat()

def fetch_youtube_channel_stats(channel_id: str, api_key: str):
    try:
        url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}"
        r = requests.get(url, timeout=15)
        js = r.json()
        items = js.get("items", [])
        if not items: return {}
        stats = items[0]["statistics"]
        return {
            "subscriberCount": int(stats.get("subscriberCount", 0)),
            "viewCount": int(stats.get("viewCount", 0)),
            "videoCount": int(stats.get("videoCount", 0)),
        }
    except Exception:
        return {}

def search_reception_queries(name: str, serp_key: str, num=5):
    try:
        from serpapi import GoogleSearch
        qs = [f"{name} controversy site:news", f"{name} fact check", f"{name} criticism", f"{name} praise review"]
        out = []
        for q in qs:
            search = GoogleSearch({"q": q, "api_key": serp_key, "num": num})
            res = search.get_dict()
            for r in res.get("organic_results", [])[:num]:
                url = r.get("link"); title = r.get("title")
                if url and title:
                    out.append((title, url))
        seen, uniq = set(), []
        for t,u in out:
            if u not in seen:
                uniq.append((t,u)); seen.add(u)
        return uniq[:num*2]
    except Exception:
        return []

def ai_sections(name, timeframe, items, affiliations_all, ideology_all, reach, controversies, openai_key):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        sample = items[:25]
        ctx = [{"title": it.get("title"), "date": it.get("date"), "desc": it.get("description"),
                "flags": {k: it.get(k) for k in ["sensational_terms","loaded_terms","us_vs_them","explicit_language","clickbait","appeal_authority","appeal_common_sense","appeal_emotion","anecdote_as_trend","monetization"]}} for it in sample]
        prompt = {
            "creator": name,
            "timeframe": timeframe,
            "affiliations": sorted(list(affiliations_all)),
            "ideologies": sorted(list(ideology_all)),
            "reach": reach,
            "controversies": controversies,
            "items_sample": ctx,
            "format_order": [
                "Overview","Content Themes & Direction","Language & Tone","Political/Ideological/Theological Views",
                "Rhetorical & Persuasive Strategies","Monetization & Consumerism","Reach & Influence",
                "Affiliations, Sponsorships, Partnerships","Reception & Controversies","Impact on Teen Viewers",
                "Parental Guidance","Conclusion & Takeaway for Parents"
            ],
            "instruction": "Write in accessible plain language for parents; identify listed topics and polarization/rhetoric explicitly; do not shorten; include uncertainties; be neutral and evidence-tied."
        }
        sys = "You draft non-partisan media profiles in clear language for parents, grounded in evidence."
        user = json.dumps(prompt)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":sys},{"role":"user","content":user}],
            temperature=0.2,
            max_tokens=1400,
        )
        return resp.choices[0].message.content
    except Exception:
        return ""
