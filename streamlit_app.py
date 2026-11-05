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
class ScheduleItem:
    time_str: str
    subject: str
    topic: str
    exam_date: str
    is_break: bool = False

def calculate_priority(exam_date: date, difficulty: int) -> float:
    days_left = max(1, (exam_date - date.today()).days)
    return (difficulty * 10.0) / days_left

def generate_schedule(subjects: List[Subject], num_days: int, start_hour: int, end_hour: int, lunch_mins: int, short_break_mins: int, long_break_mins: int):
    pool = []
    for subj in subjects:
        for topic in subj.topics:
            if not topic.completed:
                priority = calculate_priority(subj.exam_date, topic.difficulty)
                pool.append({
                    "subject": subj.name,
                    "topic": topic,
                    "priority": priority,
                    "exam_date": str(subj.exam_date)
                })
    
    pool.sort(key=lambda x: x["priority"], reverse=True)
    
    schedule_items = []
    
    # Safety check: if no topics found in the pool, return empty list immediately
    if not pool:
        return schedule_items
        
    pool_index = 0
    current_topic_hours_left = pool[0]["topic"].estimated_hours
    
    for day_offset in range(1, num_days + 1):
        current_day = date.today() + timedelta(days=day_offset)
        curr_hour = start_hour
        curr_min = 0
        
        continuous_study_hours = 0.0  # Track continuous study duration
        
        while curr_hour < end_hour and pool_index < len(pool):
            current_item = pool[pool_index]
            subject_name = current_item["subject"]
            topic_name = current_item["topic"].name
            exam_date_str = current_item["exam_date"]
            
            # Check for Lunch Break around 13:00
            if curr_hour == 13 and curr_min == 0:
                start_t = f"{curr_hour:02d}:{curr_min:02d}"
                total_min = curr_min + lunch_mins
                curr_hour += total_min // 60
                curr_min = total_min % 60
                end_t = f"{curr_hour:02d}:{curr_min:02d}"
                
                schedule_items.append(ScheduleItem(
                    time_str=f"{start_t} - {end_t}",
                    subject="🍽️ Meal Break",
                    topic=f"Lunch Break ({lunch_mins} mins)",
                    exam_date="-",
                    is_break=True
                ))
                continuous_study_hours = 0.0 
                continue

            # Check for Dinner Break around 19:00
            if curr_hour == 19 and curr_min == 0:
                start_t = f"{curr_hour:02d}:{curr_min:02d}"
                total_min = curr_min + lunch_mins
                curr_hour += total_min // 60
                curr_min = total_min % 60
                end_t = f"{curr_hour:02d}:{curr_min:02d}"
                
                schedule_items.append(ScheduleItem(
                    time_str=f"{start_t} - {end_t}",
                    subject="🍽️ Meal Break",
                    topic=f"Dinner Break ({lunch_mins} mins)",
                    exam_date="-",
                    is_break=True
                ))
                continuous_study_hours = 0.0 
                continue
            
            # Max slot size before enforcing a check/break rule
            available_slot_hours = min(2.0, end_hour - curr_hour - (curr_min / 60.0))
            if available_slot_hours <= 0:
                break
                
            work_hours = min(current_topic_hours_left, available_slot_hours)
            
            start_t = f"{curr_hour:02d}:{curr_min:02d}"
            
            total_minutes_start = curr_hour * 60 + curr_min
            total_minutes_end = int(total_minutes_start + (work_hours * 60))
            curr_hour = total_minutes_end // 60
            curr_min = total_minutes_end % 60
            end_t = f"{curr_hour:02d}:{curr_min:02d}"
            
            schedule_items.append(ScheduleItem(
                time_str=f"{start_t} - {end_t}",
                subject=subject_name,
                topic=topic_name,
                exam_date=exam_date_str,
                is_break=False
            ))
            
            current_topic_hours_left -= work_hours
            continuous_study_hours += work_hours
            
            # Handle Topic Completion or Break triggers
            if current_topic_hours_left <= 0:
                pool_index += 1
                if pool_index < len(pool):
                    current_topic_hours_left = pool[pool_index]["topic"].estimated_hours
                
                # Rule: Studied for 2 hours or less -> Short Break
                if curr_hour < end_hour:
                    s_start = f"{curr_hour:02d}:{curr_min:02d}"
                    t_min = curr_min + short_break_mins
                    curr_hour += t_min // 60
                    curr_min = t_min % 60
                    s_end = f"{curr_hour:02d}:{curr_min:02d}"
                    
                    schedule_items.append(ScheduleItem(
                        time_str=f"{s_start} - {s_end}",
                        subject="☕ Short Break",
                        topic=f"Short Break ({short_break_mins} mins)",
                        exam_date="-",
                        is_break=True
                    ))
                    continuous_study_hours = 0.0
            else:
                # Rule: Studied for more than 2 hours -> Long Break
                if continuous_study_hours > 2.0 and curr_hour < end_hour:
                    l_start = f"{curr_hour:02d}:{curr_min:02d}"
                    t_min = curr_min + long_break_mins
                    curr_hour += t_min // 60
                    curr_min = t_min % 60
                    l_end = f"{curr_hour:02d}:{curr_min:02d}"
                    
                    schedule_items.append(ScheduleItem(
                        time_str=f"{l_start} - {l_end}",
                        subject="🧘 Long Break",
                        topic=f"Intensive Study Rest Break ({long_break_mins} mins)",
                        exam_date="-",
                        is_break=True
                    ))
                    continuous_study_hours = 0.0
                    
    return schedule_items

# --- STREAMLIT UI ---
st.title("📚 Study Timetable Generator 📚")
st.caption("##### *Plan better. Ace your exams.*")
st.divider()  

# Sidebar controls for availability & breaks
st.sidebar.markdown("<h2 style='font-size: 26px; font-weight: bold;'>Your Plan</h2>", unsafe_allow_html=True)
num_days = st.sidebar.slider("Days to cover:", min_value=3, max_value=30, value=7)

start_hour = st.sidebar.slider("Daily Start Hour (24h):", min_value=0, max_value=23, value=9)
end_hour = st.sidebar.slider("Daily End Hour (24h):", min_value=0, max_value=23, value=21)

st.sidebar.divider()
st.sidebar.header('"Work with no play makes Jack a dull boy"')
lunch_mins = st.sidebar.slider("Meal Break (mins):", min_value=30, max_value=60, value=45, step=5)
short_break_mins = st.sidebar.slider("Short Break (mins):", min_value=5, max_value=15, value=10, step=5)
long_break_mins = st.sidebar.slider("Long Break (mins):", min_value=15, max_value=30, value=20, step=5)

st.sidebar.divider()
st.sidebar.header("Your Subjects & Topics")

if "saved_subjects" not in st.session_state:
    st.session_state.saved_subjects = {}

num_subjects = st.sidebar.number_input("How many subjects?", min_value=1, max_value=9, value=1, step=1, key="num_subjects_input")

for i in range(int(num_subjects)):
    st.sidebar.markdown(f"### Subject {i+1}")
    
    sub_name = st.sidebar.text_input(f"Subject Name {i+1}", key=f"sub_name_{i}")
    ex_date = st.sidebar.date_input(f"Exam Date {i+1}", min_value=date.today(), key=f"date_{i}")
    num_topics = st.sidebar.number_input(f"How many topics for Subject {i+1}?", min_value=1, max_value=10, value=1, step=1, key=f"num_topics_{i}")
    
    with st.sidebar.form(key=f"subject_form_{i}"):
        subject_topics = []
        for j in range(int(num_topics)):
            st.markdown(f"**Topic {j+1}**")
            
            top_name = st.text_input(f"Topic Name {j+1}", key=f"top_name_{i}_{j}")
            diff = st.slider(f"Difficulty {j+1} (1-5)", 1, 5, value=3, key=f"diff_{i}_{j}")
            est_hours = st.number_input(f"Hours {j+1}", min_value=0.5, max_value=4.0, value=2.0, step=0.5, key=f"hrs_{i}_{j}")
            
            if top_name:
                subject_topics.append({
                    "subject": sub_name,
                    "topic": top_name,
                    "difficulty": diff,
                    "estimated_hours": est_hours,
                    "exam_date": str(ex_date)
                })
        
        submitted = st.form_submit_button(f"Save Subject {i+1}")
        if submitted and sub_name:
            st.session_state.saved_subjects[i] = subject_topics
            st.success(f"Saved {sub_name} with {len(subject_topics)} topics!")
    
    st.sidebar.divider()

# --- MAIN SCREEN TIMETABLE GENERATION ---
st.subheader("Your Study Timetable")

if st.button("🚀 Generate Your Timetable", type="primary"):
    if end_hour <= start_hour:
        st.error("⚠️ Daily End Hour must be later than Daily Start Hour! Please adjust your sidebar settings.")
    else:
        all_combined_tasks = []
        for sub_idx, topics in st.session_state.saved_subjects.items():
            all_combined_tasks.extend(topics)
            
        if not all_combined_tasks:
            st.warning("⚠️ Please make sure you filled out your subject details and clicked the **'Save Subject'** button in the sidebar before generating your timetable!")
        else:
            subject_dict = {}
            for s in all_combined_tasks:
                s_name = s["subject"]
                if s_name not in subject_dict:
                    subject_dict[s_name] = {
                        "exam_date": datetime.strptime(s["exam_date"], "%Y-%m-%d").date(),
                        "topics": []
                    }
                
                topic_obj = Topic(
                    name=s["topic"], 
                    difficulty=s["difficulty"], 
                    estimated_hours=s["estimated_hours"]
                )
                subject_dict[s_name]["topics"].append(topic_obj)
                
            student_subjects = []
            for sub_name, data in subject_dict.items():
                student_subjects.append(Subject(
                    name=sub_name,
                    exam_date=data["exam_date"],
                    topics=data["topics"]
                ))
                
            schedule = generate_schedule(student_subjects, num_days, start_hour, end_hour, lunch_mins, short_break_mins, long_break_mins)
            
            results = []
            for item in schedule:
                results.append({
                    "Time": item.time_str,
                    "Subject": item.subject,
                    "Topic": item.topic,
                    "Exam Date": item.exam_date
                })
                    
            if results:
                df = pd.DataFrame(results)
                st.success("Timetable generated successfully with all breaks!")
                
                def style_timetable(dataframe):
                    unique_subjects = [s for s in dataframe['Subject'].unique() if not any(b in s for b in ["Break"])]
                    colors = [
                        'background-color: #ffebee; color: black;', # Soft Red
                        'background-color: #e8f5e9; color: black;', # Soft Green
                        'background-color: #e3f2fd; color: black;', # Soft Blue
                        'background-color: #fff3e0; color: black;', # Soft Orange
                        'background-color: #f3e5f5; color: black;', # Soft Purple
                        'background-color: #e0f7fa; color: black;', # Soft Cyan
                        'background-color: #fce4ec; color: black;'  # Soft Pink
                    ]
                    color_map = {subj: colors[i % len(colors)] for i, subj in enumerate(unique_subjects)}
                    
                    def color_rows(row):
                        subj = row['Subject']
                        if "Break" in subj:
                            return ['background-color: #f5f5f5; color: #666666; font-style: italic;' for _ in row]
                        return [color_map.get(subj, '') for _ in row]
                    
                    return dataframe.style.apply(color_rows, axis=1)

                styled_df = style_timetable(df)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Timetable as CSV",
                    data=csv,
                    file_name="my_study_timetable.csv",
                    mime="text/csv",
                )
            else:
                st.warning("Not enough available study slots to fit the required hours. Try widening your daily time window or increasing your total days!")