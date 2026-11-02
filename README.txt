AYYAPPA INTERNET CENTER – UPDATED

This update removes the mobile number field completely.
Student submission requires only:
- Student Name
- Upload one or more documents
- Submit

Run:
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py

If PowerShell blocks activation:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

Student page: http://127.0.0.1:5000/
Admin login: http://127.0.0.1:5000/admin/login
Admin dashboard: http://127.0.0.1:5000/admin
Advertisement settings: http://127.0.0.1:5000/admin/advertisement

Local test admin:
Username: admin
Password: ChangeMe123!

Change credentials and SECRET_KEY before online deployment.
The supplied image URLs are used for the CSC logo and Ayyappa image. If an external host blocks hotlinking or removes an image, download the image and store it in static/images, then update the URL in app.py.
