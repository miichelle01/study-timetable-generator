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
            end