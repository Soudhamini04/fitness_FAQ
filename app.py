from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import time

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

with open("data/faq.json", "r") as file:
    faq = json.load(file)

with open("data/membership.json", "r") as file:
    membership = json.load(file)

with open("data/equipment.json", "r") as file:
    equipment = json.load(file)

with open("data/trainers.json", "r") as file:
    trainers = json.load(file)

with open("data/workout_guides.json", "r") as file:
    workout_guides = json.load(file)

with open("data/analytics.json", "r") as file:
    analytics = json.load(file)

class Question(BaseModel):
    question: str
    membership_plan: str | None = None
    goal: str | None = None
    time_preference: str | None = None

def save_analytics():
    with open("data/analytics.json", "w") as file:
        json.dump(analytics, file, indent=2)

def scaledown(text):
    sentences = text.split(".")
    essential = []
    for sentence in sentences:
        sentence = sentence.strip()
        if any(word in sentence.lower() for word in ["first", "keep", "avoid", "lower", "push"]):
            essential.append(sentence)
    return ". ".join(essential) + "."

def extract_goal_and_time(text):
    goals = ["weight loss", "strength", "muscle gain", "cardio"]
    times = ["morning", "afternoon", "evening"]

    detected_goal = None
    detected_time = None

    for g in goals:
        if g in text:
            detected_goal = g

    for t in times:
        if t in text:
            detected_time = t

    return detected_goal, detected_time

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/analytics")
def get_analytics():
    return analytics

@app.post("/ask")
def ask_question(data: Question):
    start_time = time.time()
    user_q = data.question.lower()
    analytics["total_queries"] += 1

    answer = None

    goal = data.goal
    time_pref = data.time_preference

    auto_goal, auto_time = extract_goal_and_time(user_q)

    if not goal:
        goal = auto_goal
    if not time_pref:
        time_pref = auto_time

    if goal and time_pref:
        goal = goal.lower()
        time_pref = time_pref.lower()

        best_trainer = None
        best_score = 0

        for trainer in trainers:
            score = 0
            if goal in [s.lower() for s in trainer["specialties"]]:
                score += 5
            if time_pref in [t.lower() for t in trainer["availability"]]:
                score += 3
            score += trainer["experience"]

            if score > best_score:
                best_score = score
                best_trainer = trainer

        if best_trainer:
            analytics["trainer_queries"] += 1
            answer = f"Recommended Trainer: {best_trainer['name']}. Experience: {best_trainer['experience']} years. Specialties: {', '.join(best_trainer['specialties'])}."

    if not answer and ("guest" in user_q or "cancel" in user_q):
        if data.membership_plan:
            plan = data.membership_plan.lower()
            if plan in membership:
                if "guest" in user_q:
                    analytics["membership_queries"] += 1
                    answer = membership[plan]["guest_policy"]
                if "cancel" in user_q:
                    analytics["membership_queries"] += 1
                    answer = membership[plan]["cancel_policy"]

    if not answer:
        for item in equipment:
            if item.lower() in user_q:
                info = equipment[item]
                analytics["equipment_queries"] += 1
                answer = f"{item.title()} is located at {info['location']}. It is used for: {info['usage']} {info['max_time']}"

    if not answer:
        for exercise in workout_guides:
            if exercise in user_q:
                full_text = workout_guides[exercise]["full_text"]
                compressed = scaledown(full_text)
                analytics["workout_queries"] += 1
                answer = compressed

    if not answer:
        for key in faq:
            if key in user_q:
                analytics["faq_queries"] += 1
                answer = faq[key]

    if not answer:
        answer = "Sorry, I don't know the answer."

    response_time = time.time() - start_time
    analytics["total_response_time"] += response_time
    analytics["average_response_time"] = analytics["total_response_time"] / analytics["total_queries"]

    save_analytics()

    return {
        "answer": answer,
        "response_time_seconds": round(response_time, 4)
    }
