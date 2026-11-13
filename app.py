import os
from db import engine, Base, SessionLocal
import models
import json
import docx
import PyPDF2
from flask import Flask, render_template, request, redirect, session, url_for
from ai import analyze_resume 
from dotenv import load_dotenv
load_dotenv()

# Support both 'templates' and 'Templates' folder names across Windows & Linux
template_dir = "templates" if os.path.exists("templates") else "Templates"
app = Flask(__name__, template_folder=template_dir, static_folder="static")
app.secret_key = os.getenv("SECRET_KEY")

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database initialization warning: {e}")


# HOME
@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


# SIGN UP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not email or not password:
            return render_template("signup.html", error="Email and password are required.")

        db = SessionLocal()
        try:
            existing_user = db.query(models.User).filter_by(email=email).first()
            if existing_user:
                return render_template("signup.html", error="User already exists. Please login.")

            user = models.User(email=email, password=password)
            db.add(user)
            db.commit()
            return redirect("/login")
        except Exception as e:
            db.rollback()
            return render_template("signup.html", error=f"Database error: {str(e)}")
        finally:
            db.close()

    return render_template("signup.html")


# LOG IN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "").strip()

        db = SessionLocal()
        try:
            user = db.query(models.User).filter_by(email=email, password=password).first()
            if user:
                session["user"] = user.email
                return redirect("/dashboard")
            else:
                return render_template("login.html", error="Invalid email or password.")
        except Exception as e:
            return render_template("login.html", error=f"Database error: {str(e)}")
        finally:
            db.close()

    return render_template("login.html")


# DASHBOARD
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    result = None

    if request.method == "POST":
        user_goal = (request.form.get("role") or "").strip()
        resume_text = (request.form.get("resume") or "").strip()
        file = request.files.get("file")

        # file handling
        if file and file.filename != "":
            filename_lower = file.filename.lower()
            if filename_lower.endswith(".pdf"):
                try:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""
                    resume_text = text.strip()
                except Exception as e:
                    result = {"error": f"PDF error: {str(e)}"}

            elif filename_lower.endswith(".docx"):
                try:
                    doc = docx.Document(file)
                    text = ""
                    for para in doc.paragraphs:
                        text += para.text + "\n"
                    resume_text = text.strip()
                except Exception as e:
                    result = {"error": f"Docx error: {str(e)}"}
            else:
                result = {"error": "Unsupported file type. Please upload a .pdf or .docx file."}

        if result is None:
            if not user_goal:
                result = {"error": "Please enter your target role (e.g., AIML Engineer)."}
            elif not resume_text:
                result = {"error": "Please paste your resume text or upload a valid PDF/DOCX file."}
            else:
                try:
                    result = analyze_resume(resume_text, user_goal)

                    # save to db
                    db = SessionLocal()
                    try:
                        user = db.query(models.User).filter_by(email=session["user"]).first()
                        if user:
                            report = models.Reports(
                                user_id=user.id,
                                resume_text=resume_text,
                                result=json.dumps(result)
                            )
                            db.add(report)
                            db.commit()
                    except Exception as db_err:
                        db.rollback()
                        result["db_warning"] = f"Could not save report: {str(db_err)}"
                    finally:
                        db.close()

                except Exception as e:
                    result = {"error": f"AI error : {str(e)}"}

    return render_template(
        "dashboard.html",
        user=session["user"],
        result=result
    )


# HISTORY
@app.route("/history", methods=["GET", "POST"])
def history():
    if "user" not in session:
        return redirect("/login")

    parsed_reports = []
    error_msg = None

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=session["user"]).first()
        reports = db.query(models.Reports).filter_by(user_id=user.id).all() if user else []

        # convert JSON string > dict safely
        for r in reports:
            try:
                parsed_result = json.loads(r.result) if r.result else {}
                if not isinstance(parsed_result, dict):
                    parsed_result = {}
            except Exception:
                parsed_result = {}

            parsed_reports.append({
                "resume": r.resume_text or "",
                "result": parsed_result
            })
    except Exception as e:
        error_msg = f"Database error: {str(e)}"
    finally:
        db.close()

    return render_template("history.html", reports=parsed_reports, error=error_msg)


# LOG OUT
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


# FORGOT PASSWORD
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        new_password = (request.form.get("new_password") or "").strip()

        if not email or not new_password:
            return render_template("forgot_pswd.html", error="Please enter both email and new password.")

        db = SessionLocal()
        try:
            user = db.query(models.User).filter_by(email=email).first()
            if not user:
                return render_template("forgot_pswd.html", error="Account not found with this email.")

            user.password = new_password
            db.commit()
            return redirect("/login")
        except Exception as e:
            db.rollback()
            return render_template("forgot_pswd.html", error=f"Database error: {str(e)}")
        finally:
            db.close()

    return render_template("forgot_pswd.html")


if __name__ == "__main__":
    app.run(debug=True)
