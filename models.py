from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class CreatorJob(Base):
    __tablename__ = "creator_jobs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    timeframe = Column(String, default="2020–present")
    yt_channel_url = Column(Text, default="")
    podcast_rss = Column(Text, default="")
    site_rss = Column(Text, default="")
    other_links = Column(Text, default="")
    status = Column(String, default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text, default="")
    items = relationship("CollectedItem", back_populates="job", cascade="all, delete")

class CollectedItem(Base):
    __tablename__ = "collected_items"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("creator_jobs.id"), nullable=False)
    date = Column(String, default="")
    title = Column(Text, default="")
    url = Column(Text, default="")
    platform = Column(String, default="")
    description = Column(Text, default="")
    sensational_terms = Column(Text, default="")
    loaded_terms = Column(Text, default="")
    us_vs_them = Column(Boolean, default=False)
    explicit_language = Column(Boolean, default=False)
    monetization = Column(Text, default="")
    job = relationship("CreatorJob", back_populates="items")

class JobReport(Base):
    __tablename__ = "job_reports"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("creator_jobs.id"), nullable=False, unique=True)
    report_markdown = Column(Text, default="")
