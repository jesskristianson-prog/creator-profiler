import streamlit as st
import requests

st.set_page_config(page_title="Creator Profiler — Dashboard", layout="wide")
st.title("Creator Profiler — Set & Forget (AI + Web Search)")

api_url = st.text_input("API URL", value="http://127.0.0.1:8000")

st.header("Submit new creator job")
with st.form("new_job"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Creator name")
        timeframe = st.text_input("Timeframe", value="2020–present")
    with col2:
        yt = st.text_input("YouTube channel URL (with /channel/ID)")
        podcast = st.text_input("Podcast RSS (optional)")
        site = st.text_input("Website/Blog RSS (optional)")
    other = st.text_area("Other links (one per line)")
    submit = st.form_submit_button("Queue job")
    if submit:
        r = requests.post(f"{api_url}/jobs", json={
            "name": name, "timeframe": timeframe, "yt_channel_url": yt,
            "podcast_rss": podcast, "site_rss": site, "other_links": other
        })
        if r.status_code == 200:
            st.success(f"Queued job {r.json()['id']} for {name}")
        else:
            st.error(r.text)

st.header("Jobs")
r = requests.get(f"{api_url}/jobs")
if r.status_code == 200:
    jobs = r.json()
    for j in jobs:
        with st.expander(f"Job {j['id']} — {j['name']} — {j['status']}", expanded=False):
            st.write(j)
            rr = requests.get(f"{api_url}/reports/{j['id']}")
            if rr.status_code == 200:
                data = rr.json()
                st.subheader("Report Markdown")
                st.code(data.get("report_markdown","") or "(Report not generated yet)")
                st.subheader("Items (first 20)")
                st.write(data["items"][:20])
else:
    st.error("Cannot fetch jobs")
