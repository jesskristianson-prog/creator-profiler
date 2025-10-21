from pydantic import BaseModel
from typing import Optional, List

class JobCreate(BaseModel):
    name: str
    timeframe: Optional[str] = "2020–present"
    yt_channel_url: Optional[str] = ""
    podcast_rss: Optional[str] = ""
    site_rss: Optional[str] = ""
    other_links: Optional[str] = ""

class JobOut(BaseModel):
    id: int
    name: str
    timeframe: str
    status: str
    error_message: str = ""
    class Config:
        from_attributes = True

class ItemOut(BaseModel):
    date: str
    title: str
    url: str
    platform: str
    description: str
    sensational_terms: str
    loaded_terms: str
    us_vs_them: bool
    explicit_language: bool
    monetization: str

class ReportOut(BaseModel):
    job: JobOut
    items: List[ItemOut]
    report_markdown: str
