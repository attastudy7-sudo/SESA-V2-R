from flask import Blueprint, render_template, g, session, redirect, url_for, request, flash, jsonify
from app import db
from app.models import Accounts, TestResult, Question
from app.utils.decorators import login_required
from datetime import datetime

test_bp = Blueprint("test", __name__, url_prefix="/")


# -------------------------------
# Scoring ranges
# -------------------------------
scoringRanges = {
    "Separation Anxiety Disorder": [
        {"min": 0, 'max': 5, 'stage': "Normal Stage", 'message': "You're managing separation anxiety well."},
        {"min": 6, 'max': 10, 'stage': "Mild Stage", 'message': "Some signs of separation anxiety are showing."},
        {"min": 11, 'max': 16, 'stage': "Elevated Stage", 'message': "Separation anxiety is affecting school life."},
        {"min": 17, 'max': 21, 'stage': "Clinical Stage", 'message': "Professional help may be required."}
    ],
    # Add other test types in the same format
      "Social Phobia"  : [
            { "min": 0, 'max': 6, 'stage': "Normal Stage", 'message': "Your results show that you feel okay most days. You are managing your fear of being judged or embarrassed in public very well, and can cope with school and social life." },
            { "min": 7, 'max': 13, 'stage': "Mild Stage", 'message': "Your results show that you're struggling a bit more than usual. Some signs of social phobia (fear of being judged or embarrassed in public) are beginning to show (manifest) but they are still manageable." },
            { "min": 14, 'max': 20, 'stage': "Elevated Stage", 'message': "Your results show that social phobia (fear of being judged or embarrassed in public) is becoming more serious and it's affecting your school life (i.e., academics, behaviour, relational adjustments)." },
            { "min": 21, 'max': 27, 'stage': "Clinical Stage", 'message': "Your results show that your social phobia (fear of being judged or embarrassed in public) has become severe or extreme making school life very difficult. You may require a professional help including counselling and medical intervention." },
        ],
        "Generalised Anxiety Disorder": [
    { "min": 0, 'max': 4, 'stage': "Normal Stage", 'message': "Your results show that you feel okay most days. You are managing your possible worry about many things that may happen particularly in school." },
    { "min": 5, 'max': 9, 'stage': "Mild Stage", 'message': "Your results show that you're struggling a bit more than usual. Some signs of constant worrying are beginning to show but they are still manageable with the right help." },
    { "min": 10, 'max': 13, 'stage': "Elevated Stage", 'message': "Your results show that your constant worry about many things is becoming more serious and may be affecting your school life and relationships (academics, behaviour, relational adjustments)." },
    { "min": 14, 'max': 18, 'stage': "Clinical Stage", 'message': "Your results show that your constant worrying about many things has become severe and profound making school life very difficult. You may require a professional help including counselling and medical intervention." }
        ],
        "Panic Disorder": [
    { "min": 0, 'max': 6, 'stage': "Normal Stage", 'message': "Your results show that you feel okay most days. You are managing your sudden fear attacks, and you are able to cope with school and social life." },
    { "min": 7, 'max': 13, 'stage': "Mild Stage", 'message': "Your results show that you're struggling a bit more than usual. Some signs of sudden fear attacks or panic disorder are beginning to manifest but they are still manageable." },
    { "min": 14, 'max': 20, 'stage': "Elevated Stage", 'message': "Your results show that sudden fear attacks or heart racing moments are becoming more serious and may be affecting your school life and social interaction (i.e., academics, behaviour, relational adjustments)." },
    { "min": 21, 'max': 27, 'stage': "Clinical Stage", 'message': "Your results show that your sudden fear attacks or heart racing moments has become severe or extreme making school life very difficult. You may require a professional help including counselling and medical intervention." }
        ],
        "Obsessive Compulsive Disorder": [
    { "min": 0, 'max': 4, 'stage': "Normal Stage", 'message': "Your results indicate that you feel okay most days. You have little to no symptoms of uncontrollable thoughts and you are coping very well with school life." },
    { "min": 5, 'max': 9, 'stage': "Mild Stage", 'message': "Your results show that you may be struggling with repetitive thoughts. Some signs of obsessive-compulsive disorder may be manifesting but they are still manageable." },
    { "min": 10, 'max': 13, 'stage': "Elevated Stage", 'message': "Your results show that uncontrollable thoughts and ideation are becoming more serious and may be affecting your school life and social interaction (i.e., academics, behaviour, relational adjustments)." },
    { "min": 14, 'max': 18, 'stage': "Clinical Stage", 'message': "Your results show that uncontrollable thoughts have become severe or extreme making school life very difficult. You may require a professional help including counselling and medical intervention." }
        ],
        "Major Depressive Disorder": [
    { "min": 0, 'max': 7, 'stage': "Normal Stage", 'message': "Your results indicate that you feel most days. You have little to no symptoms of deep sadness or loss of interest in life generally." },
    { "min": 8, 'max': 15, 'stage': "Mild Stage", 'message': "Your results show that you may be struggling with major depressive disorder. Some symptoms of deep sadness or loss of interest in life may be showing but they are still manageable." },
    { "min": 16, 'max': 22, 'stage': "Elevated Stage", 'message': "Your results show that your loss of interest in life or deep sadness is becoming more serious and may be affecting your school life and social interaction (i.e., academics, behaviour, relational adjustments)." },
    { "min": 23, 'max': 30, 'stage': "Clinical Stage", 'message': "Your results show that your loss of interest in life has become severe or extreme making school and social life very difficult. You may require a professional help including counselling and medical intervention." }
        ],
    }

test_order = ["Separation Anxiety Disorder","Social Phobia","Generalised Anxiety Disorder","Panic Disorder","Obsessive Compulsive Disorder","Major Depressive Disorder"]

# -------------------------------
# Load logged-in user
# -------------------------------
@test_bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = Accounts.query.get(user_id) if user_id else None


# -------------------------------
# Display questions
# -------------------------------
@test_bp.route("/test/<string:test_type>", methods=["GET", "POST"])
@login_required
def display_questions(test_type):
    questions = Question.query.filter_by(test_type=test_type).all()
    if not questions:
        flash(f"No questions found for {test_type}.")
        return redirect(url_for("main.home"))

    if "current_test" not in session or session.get("current_test") != test_type:
        session["current_test"] = test_type
        session["q_index"] = 0
        session["score"] = 0

    q_index = session["q_index"]
    question_count = len(questions)

    if request.method == "POST":
        answer = request.form.get("answer")
        score_map = {"Never": 0, "Sometimes": 1, "Often": 2, "Always": 3}
        session["score"] += score_map.get(answer, 0) if answer else 0
        session["q_index"] += 1
        q_index = session["q_index"]

        if q_index >= question_count:
            total_score = session.pop("score", 0)
            session.pop("q_index", None)
            session.pop("current_test", None)
            return redirect(url_for("test.show_results", test_type=test_type, score=total_score))

        return redirect(url_for("test.display_questions", test_type=test_type))

    question = questions[q_index]
    progress = round(((q_index + 1) / question_count) * 100, 1)

    return render_template(
        "test.html",
        question=question,
        curr_question=q_index + 1,
        question_count=question_count,
        test_type=test_type,
        progress=progress
    )

@test_bp.route("/api/test/<path:test_type>/next", methods=["POST"])
def next_question_api(test_type):
    """
    Handles next/back question API for a given test type.
    Returns JSON with question text, number, and progress.
    """
    questions = Question.query.filter_by(test_type=test_type).all()
    question_count = len(questions)

    if question_count == 0:
        return jsonify({"error": f"No questions found for '{test_type}'"}), 404

    # Initialize session if new test
    if "current_test" not in session or session["current_test"] != test_type:
        session["current_test"] = test_type
        session["q_index"] = 0
        session["score"] = 0

    q_index = session["q_index"]

    data = request.get_json() or {}
    answer = data.get("answer")
    action = data.get("action")

    score_map = {"Never": 0, "Sometimes": 1, "Often": 2, "Always": 3}

    # --- Handle Back button ---
    if action == "back" and q_index > 0:
        session["q_index"] -= 1
        q_index = session["q_index"]
        question = questions[q_index]
        progress = round(((q_index + 1) / question_count) * 100, 1)
        return jsonify({
            "question_number": q_index + 1,
            "question_text": question.question_content,
            "progress": progress,
            "finished": False
        })

    # --- Handle Next/answer submission ---
    if answer:
        session["score"] += score_map.get(answer, 0)
        session["q_index"] += 1
        q_index = session["q_index"]

    # --- Check if test finished ---
    if q_index >= question_count:
        total_score = session.pop("score", 0)
        session.pop("q_index", None)
        session.pop("current_test", None)
        return jsonify({
            "finished": True,
            "redirect": url_for("test.show_results", test_type=test_type, score=total_score)
        })

    # --- Return next question ---
    question = questions[q_index]
    progress = round(((q_index + 1) / question_count) * 100, 1)
    return jsonify({
        "question_number": q_index + 1,
        "question_text": question.question_content,
        "progress": progress,
        "finished": False
    })
# -------------------------------
# Show results
# -------------------------------
@test_bp.route("/result/<string:test_type>/<int:score>")
@login_required
def show_results(test_type, score):
    ranges = scoringRanges.get(test_type, [])
    stage = "Unknown"
    message = "No result available."

    questions = Question.query.filter_by(test_type=test_type).all()
    max_score = len(questions) * 3 if questions else 0
    score_range = "0 to 0"

    for r in ranges:
        if r["min"] <= score <= r["max"]:
            stage = r["stage"]
            message = r["message"]
            score_range = f"{r['min']} to {r['max']}"
            break

    # Deter"min"e next test
    try:
        next_test_type = test_order[test_order.index(test_type) + 1]
    except (ValueError, IndexError):
        next_test_type = None

    return render_template(
        "result.html",
        test_type=test_type,
        score=score,
        stage=stage,
        message=message,
        next_test_type=next_test_type,
        max_score=max_score,
        score_range=score_range
    )


# -------------------------------
# Submit result to DB
# -------------------------------
@test_bp.route("/submit_result", methods=["POST"])
@login_required
def submit_result():
    test_type = request.form.get("test_type")
    score = request.form.get("score", type=int)
    max_score = request.form.get("max_score", type=int)   # ADD THIS
    details = request.form.get("stage")
    feedback = request.form.get("feedback")  # NEW FIELD


    if not test_type or score is None or not details:
        flash("Missing data for submission.", "danger")
        return redirect(url_for("main.home"))

    result = TestResult(
        test_type=test_type,
        user_id=g.user.id,
        score=score,
        max_score=max_score,
        details=details,
        taken_at=datetime.utcnow(),
        feedback=feedback
    )

    db.session.add(result)
    db.session.commit()

    flash("Your results have been saved!", "success")
    return redirect(url_for("main.home"))
