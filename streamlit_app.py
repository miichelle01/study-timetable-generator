import io
import streamlit as st
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List
import pandas as pd
import streamlit.components.v1 as components

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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
    difficulty_str: str
    exam_date: str
    is_break: bool = False

def calculate_priority(exam_date: date, difficulty: int) -> float:
    days_left = max(1, (exam_date - date.today()).days)
    return (float(difficulty ** 2) * 15.0) / days_left

def generate_schedule(subjects: List[Subject], num_days: int, start_hour: int, end_hour: int, lunch_mins: int, short_break_mins: int, long_break_mins: int):
    pool = []
    for subj in subjects:
        for topic in subj.topics:
            if not topic.completed:
                priority = calculate_priority(subj.exam_date, topic.difficulty)
                pool.append({
                    "subject": subj.name,
                    "topic": topic,
                    "difficulty": topic.difficulty,
                    "priority": priority,
                    "exam_date": subj.exam_date.strftime("%d/%m/%Y")
                })
    
    pool.sort(key=lambda x: x["priority"], reverse=True)
    schedule_items = []
    
    if not pool:
        return schedule_items
        
    pool_index = 0
    current_topic_hours_left = pool[0]["topic"].estimated_hours
    
    for day_offset in range(1, num_days + 1):
        curr_hour = start_hour
        curr_min = 0
        continuous_study_hours = 0.0  
        
        while curr_hour < end_hour and pool_index < len(pool):
            # Enforce meal breaks at 13:00 and 19:00 sharp
            if (curr_hour == 13 and curr_min == 0) or (curr_hour == 19 and curr_min == 0):
                start_t = f"{curr_hour:02d}:{curr_min:02d}"
                total_min = curr_min + lunch_mins
                curr_hour += total_min // 60
                curr_min = total_min % 60
                end_t = f"{curr_hour:02d}:{curr_min:02d}"
                
                schedule_items.append(ScheduleItem(
                    time_str=f"{start_t}\n{end_t}",
                    subject="Meal Break",
                    topic="",
                    difficulty_str="",
                    exam_date="",
                    is_break=True
                ))
                continuous_study_hours = 0.0 
                continue

            # Snap to meal if we are within 15 minutes of 13:00 or 19:00
            if (curr_hour == 12 and curr_min >= 45) or (curr_hour == 18 and curr_min >= 45):
                curr_hour = 13 if curr_hour == 12 else 19
                curr_min = 0
                continue

            current_item = pool[pool_index]
            subject_name = current_item["subject"]
            topic_name = current_item["topic"].name
            topic_diff = current_item["difficulty"]
            exam_date_str = current_item["exam_date"]
            diff_stars = "⭐" * topic_diff
            
            available_slot_hours = min(2.0, end_hour - curr_hour - (curr_min / 60.0))
            if available_slot_hours <= 0:
                break
                
            work_hours = min(current_topic_hours_left, available_slot_hours)
            
            start_t = f"{curr_hour:02d}:{curr_min:02d}"
            total_minutes_start = curr_hour * 60 + curr_min
            total_minutes_end = int(total_minutes_start + (work_hours * 60))
            
            target_meal = 13 if (curr_hour < 13) else (19 if (curr_hour < 19 and curr_hour >= 13) else None)
            if target_meal and total_minutes_end > (target_meal * 60):
                total_minutes_end = target_meal * 60
                work_hours = max(0.0, (total_minutes_end - total_minutes_start) / 60.0)
                if work_hours == 0:
                    curr_hour = target_meal
                    curr_min = 0
                    continue

            curr_hour = total_minutes_end // 60
            curr_min = total_minutes_end % 60
            end_t = f"{curr_hour:02d}:{curr_min:02d}"
            
            schedule_items.append(ScheduleItem(
                time_str=f"{start_t}\n{end_t}",
                subject=subject_name,
                topic=topic_name,
                difficulty_str=diff_stars,
                exam_date=exam_date_str,
                is_break=False
            ))
            
            current_topic_hours_left -= work_hours
            continuous_study_hours += work_hours

            if current_topic_hours_left <= 0:
                pool_index += 1
                if pool_index < len(pool):
                    current_topic_hours_left = pool[pool_index]["topic"].estimated_hours
                
                hits_meal = (curr_hour == 13 or curr_hour == 19) or \
                            (curr_hour == 12 and (curr_min + short_break_mins) >= 60) or \
                            (curr_hour == 18 and (curr_min + short_break_mins) >= 60)

                if pool_index < len(pool) and curr_hour < end_hour and not hits_meal:
                    s_start = f"{curr_hour:02d}:{curr_min:02d}"
                    t_min = curr_min + short_break_mins
                    curr_hour += t_min // 60
                    curr_min = t_min % 60
                    s_end = f"{curr_hour:02d}:{curr_min:02d}"
                    
                    schedule_items.append(ScheduleItem(
                        time_str=f"{s_start}\n{s_end}",
                        subject="Short Break",
                        topic="",
                        difficulty_str="",
                        exam_date="",
                        is_break=True
                    ))
                    continuous_study_hours = 0.0
            else:
                hits_meal = (curr_hour == 13 or curr_hour == 19) or \
                            (curr_hour == 12 and (curr_min + long_break_mins) >= 60) or \
                            (curr_hour == 18 and (curr_min + long_break_mins) >= 60)

                if continuous_study_hours > 2.0 and curr_hour < end_hour and pool_index < len(pool) and not hits_meal:
                    l_start = f"{curr_hour:02d}:{curr_min:02d}"
                    t_min = curr_min + long_break_mins
                    curr_hour += t_min // 60
                    curr_min = t_min % 60
                    l_end = f"{curr_hour:02d}:{curr_min:02d}"
                    
                    schedule_items.append(ScheduleItem(
                        time_str=f"{l_start}\n{l_end}",
                        subject="Long Break",
                        topic="",
                        difficulty_str="",
                        exam_date="",
                        is_break=True
                    ))
                    continuous_study_hours = 0.0
                    
    return schedule_items

def create_pdf(df):
    """Helper function to convert the pandas dataframe into a downloadable PDF binary stream."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=1, # Center
        spaceAfter=20,
        textColor=colors.HexColor('#1f1f1f')
    )
    
    elements.append(Paragraph("My Study Timetable", title_style))
    elements.append(Spacer(1, 10))
    
    # Format table data
    table_data = [list(df.columns)]
    for _, row in df.iterrows():
        table_data.append([str(row['Time']), str(row['Subject']), str(row['Topic']), str(row['Difficulty']), str(row['Exam Date'])])
        
    t = Table(table_data, colWidths=[100, 150, 250, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f2f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#31333F')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- STREAMLIT UI ---
st.title("📚 Study Timetable Generator 📚")
st.caption("##### *Plan better. Ace your exams.*")
st.divider()  

# Sidebar controls for availability & breaks
st.sidebar.markdown("<h2 style='font-size: 26px; font-weight: bold;'>Your Plan</h2>", unsafe_allow_html=True)

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
    num_topics = st.sidebar.number_input(f"How many topics for Subject