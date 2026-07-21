import os
import re
from email.utils import parseaddr
import base64
import requests
import mimetypes

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# =====================================
# GMAIL PERMISSIONS
# =====================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]


# =====================================
# GMAIL LOGIN
# =====================================

def gmail_service():

    creds = None

    if os.path.exists("token.json"):

        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    if not creds:

        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json",
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:

            token.write(
                creds.to_json()
            )

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


# =====================================
# LOAD RESUME SUMMARY
# =====================================

def load_resume():

    try:

        with open(
            "resume_summary.txt",
            "r",
            encoding="utf-8"
        ) as file:

            return file.read()

    except Exception:

        return ""


# =====================================
# OLLAMA CLASSIFICATION
# =====================================

def analyze_email(subject, body):

    resume = load_resume()

    prompt = f"""
You are a Job Matching Assistant.

Candidate Resume:

{resume}

Email Subject:
{subject}

Email Body:
{body}

Classify the email.

Return ONLY one of these:

GOOD_MATCH
PARTIAL_MATCH
NOT_MATCH
NOT_JOB
"""

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",
            
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        data = response.json()

        if "response" in data:

            result = data["response"].strip()

            if "GOOD_MATCH" in result:
                return "GOOD_MATCH"

            if "PARTIAL_MATCH" in result:
                return "PARTIAL_MATCH"

            if "NOT_MATCH" in result:
                return "NOT_MATCH"

            if "NOT_JOB" in result:
                return "NOT_JOB"

        return "ERROR"

    except Exception as e:

        print("Ollama Error:", e)

        return "ERROR"


# =====================================
# SEND EMAIL WITH RESUME
# =====================================

def send_email_with_resume(
    service,
    recipient_email,
    subject
):

    resume_file = "Lasya Reddy.docx"

    message = MIMEMultipart()

    message["to"] = recipient_email
    message["subject"] = f"Re: {subject}"

    email_body = """
Hello,

Thank you for reaching out regarding this opportunity.

I am very interested in this position and would like to learn more about the role.

Could you please share the following details?

• Client Name
• Pay Rate
• Work Location
• Contract Duration
• Interview Process

I have attached my resume for your review.

If my profile matches the requirement, please let me know. I would be happy to discuss this opportunity further.

Thank you for your time and consideration.

Best Regards,
Lasya Reddy
"""

    message.attach(
        MIMEText(
            email_body,
            "plain"
        )
    )

    if os.path.exists(resume_file):

        content_type, _ = mimetypes.guess_type(
            resume_file
        )

        if content_type:

            main_type, sub_type = content_type.split("/")

        else:

            main_type = "application"
            sub_type = "octet-stream"

        with open(
            resume_file,
            "rb"
        ) as file:

            attachment = MIMEBase(
                main_type,
                sub_type
            )

            attachment.set_payload(
                file.read()
            )

        encoders.encode_base64(
            attachment
        )

        attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="{os.path.basename(resume_file)}"'
        )

        message.attach(
            attachment
        )

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    service.users().messages().send(
        userId="me",
        body={
            "raw": raw_message
        }
    ).execute()

    print("✅ Resume Sent Successfully")


# =====================================
# EMAIL BODY EXTRACTION
# =====================================

def extract_body(payload):

    body = ""

    try:

        if "parts" in payload:

            for part in payload["parts"]:

                if part.get(
                    "mimeType"
                ) == "text/plain":

                    data = part["body"].get("data")

                    if data:

                        return base64.urlsafe_b64decode(
                            data
                        ).decode(
                            "utf-8",
                            errors="ignore"
                        )

        data = payload.get(
            "body",
            {}
        ).get("data")

        if data:

            return base64.urlsafe_b64decode(
                data
            ).decode(
                "utf-8",
                errors="ignore"
            )

    except Exception as e:

        print(
            "Body Extraction Error:",
            e
        )

    return body


# =====================================
# READ EMAILS
# =====================================

def read_emails():

    service = gmail_service()

    results = service.users().messages().list(
        userId="me",
        q="is:unread newer_than:30d -from:lasyak605@gmail.com"
    ).execute()

    messages = results.get(
        "messages",
        []
    )[:1]

    if not messages:

        print("No emails found.")
        return

    print(
        f"\nFound {len(messages)} email(s)\n"
    )

    for msg in messages:

        try:

            email = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            ).execute()

            payload = email["payload"]

            subject = ""
            sender = ""
            reply_to = ""

            for header in payload["headers"]:

                if header["name"] == "Subject":

                    subject = header["value"]

                elif header["name"] == "From":

                    sender = header["value"]

                elif header["name"].lower() == "reply-to":

                    reply_to = header["value"]

            print("=" * 60)
            print("FROM :", sender)
            print("SUBJECT :", subject)

            sender_lower = sender.lower()
            subject_lower = subject.lower()

            blocked_senders = [

                "applyonline@dice.com",
                "dice.com",
                "indeed.com",

                "jobs-noreply@linkedin.com",
                "groups-noreply@linkedin.com",
                "alerts-noreply@linkedin.com",
                "newsletters-noreply@linkedin.com",

                "glassdoor.com",
                "monster.com",
                "ziprecruiter.com",
                "careerbuilder.com",

                "newsletter"
            ]

            blocked_subjects = [

                "job alert",
                "newsletter",
                "recommended jobs",
                "daily jobs",
                "weekly jobs",
                "linkedin jobs",
                "linkedin alert",
                "apply now",
                "indeed",
                "dice"
            ]

            if any(
                item in sender_lower
                for item in blocked_senders
            ):

                print(
                    "Skipping Newsletter / Job Board"
                )

                continue

            if any(
                item in subject_lower
                for item in blocked_subjects
            ):

                print(
                    "Skipping Job Alert"
                )

                continue
            if "lasyak605@gmail.com" in sender_lower:
                print("Skipping my own email")
                continue

            body = extract_body(
                payload
            )

            result = analyze_email(
                subject,
                body
            )

            print(
                "AI RESULT :",
                result
            )

            if result == "GOOD_MATCH":

                if reply_to:

                    _, recruiter_email = parseaddr(
                        reply_to
                    )

                else:

                    _, recruiter_email = parseaddr(
                        sender
                    )

                print(
                    "Recruiter Email:",
                    recruiter_email
                )

                if not recruiter_email:

                    print("Recruiter email not found")

                    continue

                if recruiter_email.lower() == "lasyak605@gmail.com":

                    print("Skipping my own email address")

                    continue

                print("About to send resume...")

                print(
                    "Recruiter:",
                    recruiter_email
                )

                print(
                    "Resume Exists:",
                    os.path.exists(
                        "Lasya Reddy.docx"
                    )
                )

                send_email_with_resume(
                    service,
                    recruiter_email,
                    subject
                )

                print(
                    "Send function completed."
                )       

            elif result == "PARTIAL_MATCH":

                print(
                    "Manual Review Needed"
                )

            elif result == "NOT_MATCH":

                print(
                    "Not a Match"
                )

            elif result == "NOT_JOB":

                print(
                    "Not a Job Email"
                )

            else:

                print(
                    "AI Processing Error"
                )

            print()

        except Exception as e:

            import traceback
            traceback.print_exc()


# =====================================
# MAIN
# =====================================

if __name__ == "__main__":

    import time

    print("Job Email Agent Started")

    while True:

        print("Checking emails...")

        read_emails()

        print("Waiting 1 minutes...")

        time.sleep(300)