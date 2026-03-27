def generate_complaint_letter(user_name, contact_info, subject_name, law_act, law_section, law_text, grievance_details):
    """
    Generates a formal complaint letter using legal context.
    """
    template = f"""
[Your Name]: {user_name}
[Your Contact]: {contact_info}

To: {subject_name}
Date: [Insert Date]

RE: FORMAL COMPLAINT REGARDING [Insert Subject, e.g., Tenancy Deposit]

Dear {subject_name},

I am writing to formally raise a grievance regarding {grievance_details}.

I would like to draw your attention to the **{law_act}**, specifically **Section {law_section}**, which states:
"{law_text}"

Under this legislation, my rights as a [student/tenant/employee] must be respected. I believe that your current actions may be in breach of these statutory requirements.

I hope we can resolve this matter amicably. I look forward to your response within 14 days, failing which I reserve the right to seek further legal advice or escalate this to the appropriate tribunal/authority.

Yours faithfully,

{user_name}
    """
    return template.strip()

if __name__ == "__main__":
    pass
