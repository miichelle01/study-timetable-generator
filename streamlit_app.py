import streamlit as st
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List
import pandas as pd

@dataclass
class Topic:
    name: str
    difficulty: int 
    estimated_hours: float
    completed: bool = False

@dataclass
class Subject:
    name: str
    exam_date: date
    topics: List[Topic] = field(default_factory=list)

@dataclass
class StudySlot:
    date: date
    start_hour: int
    end_hour: int
    assigned_subject: str = None
    assigned_topic: str = None

def calculate_priority(exam_date: date, difficulty: int) -> float:
    days_left = max(1, (exam_date - date.today()).days)
    return (difficulty * 10.0) / days_left

def generate_available_slots(start_date: date, num_days: int, start_hour: int, end_hour: int) -> List[StudySlot]:
    generated_slots = []
    for i in range(1, num_days + 1):
        current_day = start_date + timedelta(days=i)
        current_hour = start_hour
        while current_hour + 2 <= end_hour:
            generated_slots.append(StudySlot(date=current_day, start_hour=current_hour, end_hour=current_hour + 2))
            current_hour += 2
    return generated_slots

def generate_timetable(subjects: List[Subject], available_slots: List[StudySlot]):
    pool = []
    for subj in subjects:
        for topic in subj.topics:
            if not topic.completed:
                priority = calculate_priority(subj.exam_date, topic.difficulty)
                pool.append({
                    "subject": subj.name,
                    "topic": topic,
                    "priority": priority
                })
    
    pool.sort(key=lambda x: x["priority"], reverse=True)
    
    slot_index = 0
    last_subject = None
    
    for item in pool:
        hours_needed = item["topic"].estimated_hours
        
        while hours_needed > 0 and slot_index < len(available_slots):
            slot = available_slots[slot_index]
            slot_duration = slot.end_hour - slot.start_hour
            
            if slot.assigned_subject is None:
                if item["subject"] == last_subject and len(pool) > 1 and slot_index + 1 < len(available_slots):
                    slot_index += 1
                    continue
                
                slot.assigned_subject = item["subject"]
                slot.assigned_topic = item["topic"].name
                last_subject = item["subject"]
                
                if slot_duration >= hours_needed:
                    hours_needed = 0
                else:
                    hours_needed -= slot_duration
                    slot_index += 1
            else:
                slot_index += 1
                
    return available_slots

# --- STREAMLIT UI ---
st.title("Study Timetable Generator")
st.write("Generate a custom, priority-weighted study schedule optimized for your exam deadlines!")

# Sidebar controls for availability
st.sidebar.header("Your Study Hours & Schedule")
num_days = st.sidebar.slider("Days to cover:", min_value=3, max_value=30, value=7)
start_hour = st.sidebar.slider("Daily Start Hour (24h):", min_value=8, max_value=20, value=15)
end_hour = st.sidebar.slider("Daily End Hour (24h):", min_value=start_hour + 2, max_value=23, value=20)

st.sidebar.divider()
st.sidebar.header("Add Your Subjects")

# Initialize session state for user-added subjects
if 'user_subjects' not in st.session_state:
    st.session_state.user_subjects = []

with st.sidebar.form("subject_input_form"):
    sub_name = st.text_input("Subject Name (e.g. Biology)")
    top_name = st.text_input("Topic Name (e.g. Genetics)")
    diff = st.slider("Difficulty (1-5)", 1, 5, 3)
    ex_date = st.date_input("Exam Date")
    
    submitted = st.form_submit_button("Add Subject")
    if submitted and sub_name:
        st.session_state.user_subjects.append({
            "subject": sub_name,
            "topic": top_name,
            "difficulty": diff,
            "exam_date": str(ex_date)
        })
        st.success(f"Added {sub_name}!")

# Sample data option
use_sample = st.checkbox("Use Sample Data (Math & Physics)", value=True)

subjects = []
if use_sample:
    today = date.today()
    math_exam = Subject(
        name="Mathematics",
        exam_date=today + timedelta(days=7),
        topics=[
            Topic(name="Calculus Integration", difficulty=5, estimated_hours=4.0),
            Topic(name="Trigonometry", difficulty=3, estimated_hours=2.0)
        ]
    )
    physics_exam = Subject(
        name="Physics",
        exam_date=today + timedelta(days=4),
        topics=[
            Topic(name="Electromagnetism", difficulty=5, estimated_hours=3.0),
            Topic(name="Kinematics", difficulty=2, estimated_hours=2.0)
        ]
    )
    subjects = [math_exam, physics_exam]
else:
    st.info("Custom subject entry is best managed via code, or you can keep sample data checked for your live demo!")

if st.button("Generate Timetable 🚀"):
    today = date.today()
    slots = generate_available_slots(today, num_days, start_hour, end_hour)
    schedule = generate_timetable(subjects, slots)
    
    # Format for display
    results = []
    for slot in schedule:
        if slot.assigned_subject:
            results.append({
                "Date": str(slot.date),
                "Time": f"{slot.start_hour}:00 - {slot.end_hour}:00",
                "Subject": slot.assigned_subject,
                "Topic": slot.assigned_topic
            })
            
    if results:
        df = pd.DataFrame(results)
        st.success("Timetable generated successfully!")
        st.dataframe(df, use_container_width=True)
        
        # Download CSV button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Timetable as CSV",
            data=csv,
            file_name="my_study_timetable.csv",
            mime="text/csv",
        )
    else:
        st.warning("Not enough available slots to fit the required study hours. Try increasing your daily study window or days!")
