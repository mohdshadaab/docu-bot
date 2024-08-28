import streamlit as st
import requests

# FastAPI backend URL
backend_url = "http://localhost:8000"

# Initialize session state for tracking authentication and user state
if 'access_token' not in st.session_state:
    st.session_state.access_token = None

def login_user(email, password):
    # Request to log in and get a JWT token
    response = requests.post(f"{backend_url}/token", data={"username": email, "password": password})
    if response.status_code == 200:
        token_data = response.json()
        st.session_state.access_token = token_data['access_token']
        st.success("Logged in successfully!")
    else:
        st.error("Failed to log in. Check your email and password.")

def register_user(email, password):
    # Request to register a new user
    response = requests.post(f"{backend_url}/register/", json={"email": email, "password": password})
    if response.status_code == 200:
        token_data = response.json()
        st.session_state.access_token = token_data['access_token']
        st.success("Registered successfully and logged in!")
    else:
        st.error("Failed to register. The email might be taken.")

def query_chatbot(framework, question):
    # Request to query the chatbot
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    response = requests.post(f"{backend_url}/query", json={"framework": framework, "question": question}, headers=headers)
    if response.status_code == 200:
        return response.json()['answer']
    else:
        st.error("Failed to get a response from the chatbot.")
        return None

def get_chat_history(framework):
    # Request to get chat history filtered by framework
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    response = requests.get(f"{backend_url}/history/?framework={framework}", headers=headers)
    if response.status_code == 200:
        return response.json()['history']
    else:
        st.error("Failed to retrieve chat history.")
        return None

# Authentication Section
st.sidebar.title("Authentication")

if st.session_state.access_token:
    st.sidebar.success("You are logged in.")
    if st.sidebar.button("Logout"):
        st.session_state.access_token = None
        st.experimental_rerun()  # Clear the UI state and rerun the app
else:
    auth_choice = st.sidebar.selectbox("Select an option", ["Login", "Register"])

    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if auth_choice == "Login":
        if st.sidebar.button("Login"):
            login_user(email, password)
    elif auth_choice == "Register":
        if st.sidebar.button("Register"):
            register_user(email, password)

# Main Application Section
if st.session_state.access_token:
    st.title("Framework Documentation Chatbot")

    chatbot_option = st.sidebar.radio("Choose a chatbot:", ["FastAPI Chatbot", "Django Chatbot", "Ruby on Rails Chatbot", "Flutter Chatbot"])

    if chatbot_option == "FastAPI Chatbot":
        framework = "FastAPI"
        st.subheader("Ask me anything about FastAPI")
    elif chatbot_option == "Django Chatbot":
        framework = "Django"
        st.subheader("Ask me anything about Django")
    elif chatbot_option == "Ruby on Rails Chatbot":
        framework = "RubyOnRails"
        st.subheader("Ask me anything about Ruby On Rails")
    elif chatbot_option == "Flutter Chatbot":
        framework = "Flutter"
        st.subheader("Ask me anything about Flutter")

    # Input for the chatbot
    question = st.text_area(f"Enter your question about {framework}")

    # Submit button
    if st.button("Submit"):
        if question:
            answer = query_chatbot(framework, question)
            if answer:
                st.write(f"**Answer:** {answer}")
        else:
            st.error("Please enter a question.")

    # Chat History Section
    st.subheader("Chat History")
    history = get_chat_history(framework)  # Pass the selected framework to the history function
    if history:
        for entry in history:
            # Create an expander for each question
            with st.expander(f"Question: {entry['question']}"):
                st.write(f"**Answer:** {entry['answer']}")
                st.write(f"**Timestamp:** {entry['timestamp']}")
else:
    st.title("Please log in or register to use the chatbot.")
