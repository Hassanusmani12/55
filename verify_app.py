import os
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

def run_verification():
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    server_process = subprocess.Popen(["python3", "app.py"], env=env)

    # Poll server until ready
    for i in range(15):
        try:
            req = urllib.request.urlopen("http://127.0.0.1:5000/login", timeout=2)
            if req.status == 200:
                print("Server is ready!")
                break
        except Exception:
            time.sleep(1)

    screenshots_dir = os.path.join(os.path.dirname(__file__), "verification_screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            # 1. Login Page
            page.goto("http://127.0.0.1:5000/login")
            page.screenshot(path=os.path.join(screenshots_dir, "01_login.png"))

            # 2. Login as Admin
            page.fill("input[name='email']", "admin@gmail.com")
            page.fill("input[name='password']", "admin123")
            page.click("button[type='submit']")
            page.wait_for_selector("text=System Administration")
            page.screenshot(path=os.path.join(screenshots_dir, "02_admin_dashboard.png"))

            # 3. Admin Support Desk
            page.goto("http://127.0.0.1:5000/admin/support")
            page.wait_for_selector("text=Support Ticket Desk")
            page.screenshot(path=os.path.join(screenshots_dir, "03_admin_support.png"))

            # 4. Logout & Login as Analyst
            page.goto("http://127.0.0.1:5000/logout")
            page.fill("input[name='email']", "analyst@gmail.com")
            page.fill("input[name='password']", "analyst123")
            page.click("button[type='submit']")
            page.wait_for_selector("text=EduPredict Telemetry")
            page.screenshot(path=os.path.join(screenshots_dir, "04_analyst_dashboard.png"))

            # 5. Logout & Login as Teacher
            page.goto("http://127.0.0.1:5000/logout")
            page.fill("input[name='email']", "teacher@gmail.com")
            page.fill("input[name='password']", "teacher123")
            page.click("button[type='submit']")
            page.wait_for_selector("text=Instructor Portal")
            page.screenshot(path=os.path.join(screenshots_dir, "05_teacher_dashboard.png"))

            # 6. Logout & Signup new Student
            page.goto("http://127.0.0.1:5000/logout")
            page.goto("http://127.0.0.1:5000/signup")
            page.fill("input[name='email']", "student1@gmail.com")
            page.fill("input[name='password']", "student123")
            page.click("button[type='submit']")

            # Login as new Student
            page.fill("input[name='email']", "student1@gmail.com")
            page.fill("input[name='password']", "student123")
            page.click("button[type='submit']")
            page.wait_for_selector("text=Student Portal")
            page.screenshot(path=os.path.join(screenshots_dir, "06_student_dashboard.png"))

            # 7. Support Ticket Page
            page.goto("http://127.0.0.1:5000/support")
            page.wait_for_selector("text=Help & Support")
            page.screenshot(path=os.path.join(screenshots_dir, "07_support.png"))

            # 8. Notifications Page
            page.goto("http://127.0.0.1:5000/notifications")
            page.wait_for_selector("text=Notifications & Alerts")
            page.screenshot(path=os.path.join(screenshots_dir, "08_notifications.png"))

            browser.close()
            print("Verification screenshots generated successfully!")

    finally:
        server_process.terminate()

if __name__ == "__main__":
    run_verification()
