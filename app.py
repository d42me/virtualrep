from openai import OpenAI
import json
import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import time

load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


# Function to create an assistant
def create_assistant():
    assistant = client.beta.assistants.create(
        name="VirtualRep",
        instructions="You are a virtual customer. Answer questions briefly, in a sentence or less.",
        model="gpt-4-1106-preview",
    )
    print("Assistant created with id:")
    print(assistant.id)
    return assistant.id


# Function to process uploaded customer profiles
def process_file(uploaded_file, assistant_id):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        print(df)

        json_data = df.to_json()
        with open("tmp.json", "w") as f:
            f.write(json_data)

        file = client.files.create(
            file=open("tmp.json", "rb"),
            purpose="assistants",
        )
        print(file.id)

        client.beta.assistants.update(
            assistant_id,
            tools=[{"type": "retrieval"}],
            file_ids=[file.id],
        )

        return df

    else:
        return None


# Function to create a thread
def create_thread():
    thread = client.beta.threads.create()
    return thread.id


# Function to add message to the thread
def add_message_to_thread(thread_id, message, role="user"):
    message = client.beta.threads.messages.create(
        thread_id=thread_id, role=role, content=message
    )
    return message.id


# Function to wait on run
def wait_on_run(thread_id, run_id):
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    print(run.status)
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        time.sleep(0.5)
    return run


def show_json(obj):
    print(json.loads(obj.model_dump_json()))


# Streamlit app
st.title("VirtualRep Chatbot")

# Session state to hold conversation history and assistant id
if "history" not in st.session_state:
    st.session_state.history = []
if "assistant_id" not in st.session_state:
    st.session_state.assistant_id = create_assistant()
    print(st.session_state.assistant_id)

# Company Information Input
company_info = st.text_input("Enter your company information:")

# Customer Profiles File Upload
uploaded_file = st.file_uploader("Upload customer profile file", type=["csv", "xlsx"])
customer_data = process_file(uploaded_file, assistant_id=st.session_state.assistant_id)

# Chat Interface
user_input = st.text_area("Ask a question to the virtual customer:")

if st.button("Send"):
    if user_input and customer_data is not None:
        # Create a thread and add the user message
        thread_id = create_thread()
        message_id = add_message_to_thread(thread_id, user_input)

        print(thread_id)
        # Create a run and wait for its completion
        run_id = client.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=st.session_state.assistant_id
        )
        time.sleep(5)

        # Retrieve the messages again after the run completes
        messages = client.beta.threads.messages.list(thread_id=thread_id)

        # Retrieve the assistant's response
        for message in messages:
            print(json.loads(message.model_dump_json()))

            if message.role == "assistant":
                virtual_response = message.content[0].text.value
                print(virtual_response)

                # Update conversation history
                st.session_state.history.append(("User", user_input))
                st.session_state.history.append(("Virtual Customer", virtual_response))

# Display the conversation history
for role, message in st.session_state.history:
    st.text_area(f"{role}:", value=message, height=50, key=f"{role}_{message}")
