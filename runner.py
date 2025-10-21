from sqlalchemy.orm import Session
from . import models
from .utils import (
    parse_generic_rss, yt_channel_id_from_url, yt_rss_from_channel_id, analyze_text, monetization_signals,
    build_chicago_note, today_iso, fetch_youtube_channel_stats, search_reception_queries, ai_sections
)
import os

SECTION_ORDER = [
    "Overview","Content Themes & Direction","Language & Tone","Political/Ideological/Theological Views",
    "Rhetorical & Persuasive Strategies","Monetization & Consumerism","Reach & Influence",
    "Affiliations, Sponsorships, Partnerships","Reception & Controversies","Impact on Teen Viewers",
    "Parental Guidance","Conclusion & Takeaway for Parents","Factuality Score (Heuristic)","Footnotes"
]

def run_job(db: Session, job: models.CreatorJob):
    refs, items = [], []
    channel_id = ""
    if job.yt_channel_url:
        channel_id = yt_channel_id_from_url(job.yt_channel_url)
        if channel_id:
            rss = yt_rss_from_channel_id(channel_id)
            y_items = parse_generic_rss(rss, limit=40)
            for it in y_items:
                analysis = analyze_text((it.get("title","") + " " + it.get("description","")))
                it.update(analysis)
                it["monetization"] = monetization_signals(it.get("description",""))
                it["platform"] = "YouTube"
            items.extend(y_items)
            refs.append(build_chicago_note(rss, "YouTube Channel RSS feed", today_iso()))
    if job.podcast_rss:
        p_items = parse_generic_rss(job.podcast_rss, limit=40)
        for it in p_items:
            analysis = analyze_text((it.get("title","") + " " + it.get("description","")))
            it.update(analysis)
            it["monetization"] = monetization_signals(it.get("description",""))
            it["platform"] = "Podcast"
        items.extend(p_items)
        refs.append(build_chicago_note(job.podcast_rss, "Podcast RSS feed", today_iso()))
    if job.site_rss:
        s_items = parse_generic_rss(job.site_rss, limit=40)
        for it in s_items:
            analysis = analyze_text((it.get("title","") + " " + it.get("description","")))
            it.update(analysis)
            it["monetization"] = monetization_signals(it.get("description",""))
            it["platform"] = "Website/Blog"
        items.extend(s_items)
        refs.append(build_chicago_note(job.site_rss, "Website/Blog RSS feed", today_iso()))
    if job.other_links:
        for line in job.other_links.splitlines():
            u = line.strip()
            if u:
                refs.append(build_chicago_note(u, "Additional source", today_iso()))

    db.query(models.CollectedItem).filter_by(job_id=job.id).delete()
    for it in items:
        db.add(models.CollectedItem(
            job_id=job.id, date=it.get("date",""), title=it.get("title",""), url=it.get("url",""),
            platform=it.get("platform",""), description=it.get("description",""),
            sensational_terms=it.get("sensational_terms",""), loaded_terms=it.get("loaded_terms",""),
            us_vs_them=bool(it.get("us_vs_them", False)), explicit_language=bool(it.get("explicit_language", False)),
            monetization=it.get("monetization","")
        ))
    db.commit()

    total = max(1, len(items))
    sensational_rate = sum(1 for it in items if it.get("sensational_terms"))/total
    us_them_rate = sum(1 for it in items if it.get("us_vs_them"))/total
    explicit_rate = sum(1 for it in items if it.get("explicit_language"))/total
    monetized_rate = sum(1 for it in items if it.get("monetization"))/total

    affiliations_all = set(sum([it.get("affiliations_found","" ).split(", ") for it in items if it.get("affiliations_found")], []))
    affiliations_all = {a for a in affiliations_all if a}
    ideology_all = set(sum([it.get("ideology_hits","" ).split(", ") for it in items if it.get("ideology_hits")], []))
    ideology_all = {a for a in ideology_all if a}

    reach = {}
    yapi = os.getenv("YOUTUBE_API_KEY","" ).strip()
    if yapi and channel_id:
        reach = fetch_youtube_channel_stats(channel_id, yapi)

    controversies = []
    serp = os.getenv("SERPAPI_KEY","" ).strip()
    if serp:
        controversies = search_reception_queries(job.name, serp, num=5)
        for title, url in controversies:
            refs.append(build_chicago_note(url, title, today_iso()))

    source_transparency = 10 if monetized_rate>0 else 15
    evidence_quality = 10
    corrections_culture = 5
    context_discipline = 10 if sensational_rate<0.2 else 5
    headline_alignment = 6 if sensational_rate<0.2 else 3
    total_score = min(25,source_transparency)+min(25,evidence_quality)+min(20,corrections_culture)+min(20,context_discipline)+min(10,headline_alignment)

    ai_text = ""
    oai = os.getenv("OPENAI_API_KEY","" ).strip()
    if oai:
        ai_text = ai_sections(job.name, job.timeframe, items, affiliations_all, ideology_all, reach, controversies, oai)

    footnotes = "\n".join([f"[{i+1}] {r}" for i,r in enumerate(refs)])
    examples = ", ".join([it["title"] for it in items[:3]]) if items else ""
    reach_line = ""
    if reach:
        reach_line = f"- YouTube: {reach.get('subscriberCount',0):,} subscribers; {reach.get('viewCount',0):,} total views; {reach.get('videoCount',0):,} videos."

    header_md = f"""Overview
Creator: {job.name}
Primary Platform(s): YouTube, podcasts, social media
Timeframe: {job.timeframe}

Content Themes & Direction
- Auto-collected {len(items)} items across provided feeds. Examples: {examples}

Language & Tone
- Sensational phrasing in ~{sensational_rate:.0%} of titles/descriptions.
- 'Us vs. them' framing in ~{us_them_rate:.0%}; explicit language in ~{explicit_rate:.0%}.

Political/Ideological/Theological Views
- Detected ideology mentions: {', '.join(sorted(ideology_all)) or 'None auto-detected'}
- Topics to review manually: culture war themes, moral framing, theological references if present.

Rhetorical & Persuasive Strategies
- Clickbait/exaggeration indicators present: {any(it.get('clickbait') for it in items)}
- Anecdote-as-trend present: {any(it.get('anecdote_as_trend') for it in items)}
- Appeals: authority={any(it.get('appeal_authority') for it in items)}, common-sense={any(it.get('appeal_common_sense') for it in items)}, emotion={any(it.get('appeal_emotion') for it in items)}

Monetization & Consumerism
- Monetization signals detected in ~{monetized_rate:.0%} of items (sponsor/promo/affiliate/membership/merch).

Reach & Influence
{reach_line or '- RSS does not expose audience counts; add API keys to auto-fill reach metrics.'}

Affiliations, Sponsorships, Partnerships
- Auto-detected mentions: {', '.join(sorted(affiliations_all)) or 'None auto-detected'} (validate manually for actual relationships).

Reception & Controversies
- Auto-fetched links: {len(controversies)} added to footnotes (if web search enabled).

Impact on Teen Viewers
- Potential emotional effects if sensational or polarized framing is frequent; discuss evidence quality and rhetoric.

Parental Guidance
- Watch for sensationalism, explicit language, polarizing frames, sponsor pushes. Conversation starters: "What is the claim?", "What evidence is offered?", "Who benefits?"

Conclusion & Takeaway for Parents
- Automated first pass; confirm with manual sampling before high-stakes conclusions.

Factuality Score (Heuristic)
- Total: {total_score}/100 (preliminary; driven by sensationalism rate and sourcing proxies).

---
Footnotes
{footnotes}
"""

    final_md = (ai_text.strip()+"\n\n" if ai_text else "") + header_md
    rep = db.query(models.JobReport).filter_by(job_id=job.id).first()
    if not rep:
        rep = models.JobReport(job_id=job.id, report_markdown=final_md)
        db.add(rep)
    else:
        rep.report_markdown = final_md
    db.commit()

    os.makedirs("reports", exist_ok=True)
    with open(f"reports/job_{job.id}.md", "w", encoding="utf-8") as f:
        f.write(final_md)
