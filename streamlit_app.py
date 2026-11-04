import streamlit as st
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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
st.title("📚Study Timetable Generator📚")
st.caption("##### *Plan better. Ace your exams.*")
st.divider()  

# Main content starts cleanly below the line:
st.subheader("Your Generated Timetable")

# Sidebar controls for availability
st.sidebar.header("Timetable Settings")
num_days = st.sidebar.slider("Days to cover:", min_value=3, max_value=30, value=7)
start_hour = st.sidebar.slider("Daily Start Hour (24h):", min_value=8, max_value=20, value=15)
end_hour = st.sidebar.slider("Daily End Hour (24h):", min_value=start_hour + 2, max_value=23, value=20)

st.sidebar.divider()
st.sidebar.header("Your Subjects & Topics")

# Default to 1 subject
num_subjects = st.sidebar.number_input("How many subjects?", min_value=1, max_value=10, value=1, step=1, key="num_subjects_input")

if "user_subjects" not in st.session_state:
    st.session_state.user_subjects = []

all_subject_tasks = []

# Loop through each subject
for i in range(int(num_subjects)):
    st.sidebar.markdown(f"### Subject {i+1}")
    sub_name = st.sidebar.text_input(f"Subject Name {i+1}", key=f"sub_name_{i}")
    ex_date = st.sidebar.date_input(f"Exam Date {i+1}", min_value=date.today(), key=f"date_{i}")
    
    # Default to 1 topic per subject
    num_topics = st.sidebar.number_input(f"How many topics for Subject {i+1}?", min_value=1, max_value=10, value=1, step=1, key=f"num_topics_{i}")
    
    with st.sidebar.form(key=f"subject_form_{i}"):
        subject_topics = []
        for j in range(int(num_topics)):
            st.markdown(f"**Topic {j+1}**")
            top_name = st.text_input(f"Topic Name {j+1}", key=f"top_name_{i}_{j}")
            diff = st.slider(f"Difficulty {j+1} (1-5)", 1, 5, 3, key=f"diff_{i}_{j}")
            
            if top_name:
                subject_topics.append({
                    "subject": sub_name,
                    "topic": top_name,
                    "difficulty": diff,
                    "exam_date": str(ex_date)
                })
        
        submitted = st.form_submit_button(f"Save Subject {i+1}")
        if submitted and sub_name:
            all_subject_tasks.extend(subject_topics)
            st.success(f"Saved {sub_name} with {len(subject_topics)} topics!")
    
    st.sidebar.divider()

if all_subject_tasks:
    st.session_state.user_subjects = all_subject_tasks
if st.button("Generate Your Timetable"):
    today = date.today()
    slots = generate_available_slots(today, num_days, start_hour, end_hour)
    
    # Check if the student has added any subjects first
    if not st.session_state.get('user_subjects'):
        st.warning("Please add at least one subject in the sidebar before generating your timetable!")
    else:
        # Convert student input dicts back into your Subject objects so your algorithm understands them
        student_subjects = []
        for s in st.session_state.user_subjects:
            # Create a Topic object for the subject
            topic_obj = Topic(
                name=s["topic"], 
                difficulty=s["difficulty"], 
                estimated_hours=2.0  # Default study hours per topic slot
            )
            # Create the Subject object with the parsed exam date
            sub_obj = Subject(
                name=s["subject"], 
                exam_date=datetime.strptime(s["exam_date"], "%Y-%m-%d").date(), 
                topics=[topic_obj]
            )
            student_subjects.append(sub_obj)
            
        # Now generate the timetable using the student's custom subjects!
        schedule = generate_timetable(student_subjects, slots)
        
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
