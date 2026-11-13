import io
import os
import json
import docx

# Use in-memory SQLite for fast, isolated automated testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import app as flask_app
from db import Base, engine
import models

def run_all_tests():
    print("=======================================================")
    print("  RUNNING AI CAREER COPILOT - FULL TEST SUITE")
    print("=======================================================")

    flask_app.app.config["TESTING"] = True
    Base.metadata.create_all(bind=engine)
    client = flask_app.app.test_client()

    # Test 1: Unauthenticated redirect
    r = client.get("/dashboard")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    print("[PASS] Test 1: Unauthenticated access redirects to /login")

    # Test 2: Signup & Duplicate User Exception Handling
    r = client.post("/signup", data={"email": "test@aiml.com", "password": "password123"}, follow_redirects=True)
    assert r.status_code == 200
    r_dup = client.post("/signup", data={"email": "test@aiml.com", "password": "password123"})
    assert b"User already exists" in r_dup.data
    print("[PASS] Test 2: Signup works & duplicate user exception handled cleanly")

    # Test 3: Invalid Login Exception Handling
    r_bad = client.post("/login", data={"email": "test@aiml.com", "password": "wrongpassword"})
    assert b"Invalid email or password" in r_bad.data
    print("[PASS] Test 3: Invalid login credentials handled cleanly")

    # Test 4: Forgot Password Flow & Unknown Email Handling
    r_fp_bad = client.post("/forgot-password", data={"email": "nobody@aiml.com", "new_password": "newpassword123"})
    assert b"Account not found" in r_fp_bad.data
    r_fp_ok = client.post("/forgot-password", data={"email": "test@aiml.com", "new_password": "newpassword123"}, follow_redirects=True)
    assert r_fp_ok.status_code == 200
    print("[PASS] Test 4: Forgot password updates password & handles non-existent email")

    # Test 5: Valid Login & GET /dashboard Render (Previously crashed with TypeError)
    r_login = client.post("/login", data={"email": "test@aiml.com", "password": "newpassword123"}, follow_redirects=True)
    assert r_login.status_code == 200
    assert b"Welcome, test@aiml.com" in r_login.data
    print("[PASS] Test 5: Login succeeds & GET /dashboard renders without TypeError")

    # Test 6: Dashboard Missing Input Exception Handling
    r_empty = client.post("/dashboard", data={"role": "", "resume": ""})
    assert b"Please enter your target role" in r_empty.data
    print("[PASS] Test 6: Empty form submission on /dashboard handled cleanly")

    # Test 7: Dashboard Corrupted PDF & DOCX Exception Handling
    bad_pdf = (io.BytesIO(b"not a valid pdf content"), "broken.pdf")
    r_bad_pdf = client.post("/dashboard", data={"role": "AIML Engineer", "file": bad_pdf}, content_type="multipart/form-data")
    assert b"PDF error:" in r_bad_pdf.data

    bad_docx = (io.BytesIO(b"not a valid docx content"), "broken.docx")
    r_bad_docx = client.post("/dashboard", data={"role": "AIML Engineer", "file": bad_docx}, content_type="multipart/form-data")
    assert b"Docx error:" in r_bad_docx.data
    print("[PASS] Test 7: Corrupted PDF & DOCX uploads caught by exception handler")

    # Test 8: Valid DOCX Resume Upload & AI Analysis Flow
    # Mock analyze_resume so test runs offline deterministically while also testing ai.py's own error handler
    import ai
    err_res = ai.analyze_resume("Sample text", "AIML Engineer")
    assert "interview_questions" in err_res and isinstance(err_res["interview_questions"], list)
    print("[PASS] Test 8: ai.py exception handler returns valid dict with 'interview_questions' key")

    flask_app.analyze_resume = lambda text, goal: {
        "skills": ["Python", "SQL", "Flask"],
        "missing_skills": ["PyTorch", "Docker", "MLOps"],
        "roadmap": ["Learn Deep Learning with PyTorch", "Containerize ML models with Docker"],
        "projects": ["End-to-End AI Resume Analyser with TiDB"],
        "interview_questions": ["Explain bias-variance tradeoff.", "How do you deploy an ML model?"]
    }

    docx_buf = io.BytesIO()
    d = docx.Document()
    d.add_paragraph("Rohan Sharma - Skills: Python, SQL, Flask, Machine Learning")
    d.save(docx_buf)
    docx_buf.seek(0)

    r_ok = client.post(
        "/dashboard",
        data={"role": "AIML Engineer", "file": (docx_buf, "resume.docx")},
        content_type="multipart/form-data"
    )
    assert r_ok.status_code == 200
    assert b"PyTorch" in r_ok.data
    assert b"Explain bias-variance tradeoff." in r_ok.data
    print("[PASS] Test 9: Valid DOCX upload parsed, analyzed, rendered & saved to DB")

    # Test 10: History Route Rendering (Previously crashed with UndefinedError: 'result' is undefined)
    r_hist = client.get("/history")
    assert r_hist.status_code == 200
    assert b"Rohan Sharma" in r_hist.data
    assert b"PyTorch" in r_hist.data
    print("[PASS] Test 10: GET /history renders saved reports without Jinja2 UndefinedError")

    # Test 11: Logout Flow
    r_out = client.get("/logout", follow_redirects=True)
    assert r_out.status_code == 200
    assert b"Welcome Back" in r_out.data
    print("[PASS] Test 11: Logout clears session and redirects to /login")

    print("=======================================================")
    print("  ALL 11 TEST CASES PASSED SUCCESSFULLY (100% READY!)")
    print("=======================================================")

if __name__ == "__main__":
    run_all_tests()
