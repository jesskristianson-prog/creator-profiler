from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import Base, engine, SessionLocal
import models, schemas
from runner import run_job

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Creator Profiler — Queued (AI + Web Search)")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def process_queue():
    db = SessionLocal()
    try:
        pending = db.query(models.CreatorJob).filter(models.CreatorJob.status.in_(["queued","running"]))\
                 .order_by(models.CreatorJob.created_at.asc()).all()
        for job in pending:
            try:
                job.status = "running"; db.commit(); db.refresh(job)
                run_job(db, job)
                job.status = "done"; job.error_message = ""; db.commit()
            except Exception as e:
                job.status = "error"; job.error_message = str(e); db.commit()
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(process_queue, IntervalTrigger(seconds=60))
scheduler.start()

@app.post("/jobs", response_model=schemas.JobOut)
def submit_job(payload: schemas.JobCreate, db: Session = Depends(get_db)):
    job = models.CreatorJob(name=payload.name.strip(), timeframe=(payload.timeframe or "2020–present").strip(),
                            yt_channel_url=payload.yt_channel_url or "", podcast_rss=payload.podcast_rss or "",
                            site_rss=payload.site_rss or "", other_links=payload.other_links or "")
    db.add(job); db.commit(); db.refresh(job)
    return job

@app.get("/jobs", response_model=list[schemas.JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(models.CreatorJob).order_by(models.CreatorJob.created_at.desc()).all()

@app.get("/jobs/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.CreatorJob).get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    return job

@app.get("/reports/{job_id}", response_model=schemas.ReportOut)
def get_report(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.CreatorJob).get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    items = db.query(models.CollectedItem).filter_by(job_id=job_id).all()
    rep = db.query(models.JobReport).filter_by(job_id=job_id).first()
    md = rep.report_markdown if rep else ""
    return {"job": job, "items": [{"date": it.date, "title": it.title, "url": it.url, "platform": it.platform,
            "description": it.description, "sensational_terms": it.sensational_terms, "loaded_terms": it.loaded_terms,
            "us_vs_them": it.us_vs_them, "explicit_language": it.explicit_language, "monetization": it.monetization} for it in items],
            "report_markdown": md}
