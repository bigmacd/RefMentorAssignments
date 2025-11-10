import streamlit as st
import uuid
from streamlit_calendar import calendar



event_to_add = {
    "title": "New Event",
    "start": "2024-09-01",
    "end": "2024-09-02",
    "resourceId": "a",
}


options = {
    "editable": True,
    "selectable": True,
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,listMonth"
    }
}

if "CalendarKey" not in st.session_state:
    st.session_state["CalendarKey"] = str(uuid.uuid4())
events = [{"title": "Conference", "start": "2025-09-15", "end": "2025-09-17"}]
cal_data = calendar(events=events, options=options, key="CalendarKey")
st.write("Interaction ", cal_data)

if st.button("Add Event"):
    events.append(event_to_add)
    st.session_state["CalendarKey"] = str(uuid.uuid4())  # Refresh calendar
    st.rerun()  # Rerun app to reflect changes
