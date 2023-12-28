import os
import openai
import time
import streamlit as st
from dotenv import load_dotenv
import time
from io import BytesIO

# Load environment variables from .env file
load_dotenv()

# Set OpenAI API key
openai.api_key = "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"

# Create a client instance
client = openai.Client(api_key="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")

def get_response(assistant_id):
    # Check if 'messages' key is not in session_state
    if "messages" not in st.session_state:
    # If not present, initialize 'messages' as an empty list
        st.session_state.messages = []
    # Iterate through messages in session_state
    for message in st.session_state.messages:
    # Display message content in the chat UI based on the role
        with st.chat_message(message["role"]):
            st.markdown(message["content"])    
    # Get user input from chat and proceed if a prompt is entered
    if prompt := st.chat_input("Enter your message here"):
        # Add user input as a message to session_state
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user's message in the chat UI
        with st.chat_message("user"):
            st.markdown(prompt)
        # Process the assistant's response
        getResponse(assistant_id, prompt)

def getResponse(assistant_id, prompt):
    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
    thread_id = st.session_state.thread_id    


    for files in st.session_state.uploaded_files_list:
        client.beta.assistants.files.create(
            assistant_id=assistant_id,
            file_id=files
        )

    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content= prompt,
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        )

    while True:  # Change to an infinite loop to continually check for completion
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run.status == "completed":
            break  # Exit the loop once the run is completed
        time.sleep(0.5)
    
    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )

    last_message = messages.data[0].content[0].text.value

    st.session_state.messages.append({"role": "assistant", "content": last_message})
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(last_message)

def get_assistant_id(assistant_name):
    assistant_id_map = {
        "Parent": "asst_Gdc9ko8iWyvwlzpPo6PtJ0za",
        "Therapist": "asst_VhOM66PyjKYgzdo01blWVisC",
        "Teacher": "asst_HCYh7jTvoHP5IeuTl078JFpu",
    }
    
    return assistant_id_map.get(assistant_name)

def send_to_openai(file):
    try:
        local_file_path = os.path.join(os.getcwd(), file.name)  # Save the file in the working directory
        with open(local_file_path, "wb") as f:
            f.write(file.read())
        
        # Send file path to OpenAI
        with open(local_file_path, "rb") as file:
            response = client.files.create(
                file=file,
                purpose="assistants"
            )
                    
        os.remove(local_file_path)

        return response
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    st.title('Tennis Oracle - AI Assistants')

    # Initialize uploaded_files_list in st.session_state if it doesn't exist
    if "uploaded_files_list" not in st.session_state:
        st.session_state.uploaded_files_list = []
        st.session_state.sent_files = set()

    st.sidebar.title("Document Processing")
    assistant_name = st.sidebar.selectbox('Choose an assistant', ["Select Category", "Parent", "Therapist", "Teacher"])
    uploaded_files = st.sidebar.file_uploader("Upload files", accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_identifier = uploaded_file.name
            if file_identifier not in st.session_state.sent_files:
                retrieval_file = send_to_openai(uploaded_file)
                st.session_state.uploaded_files_list.append(retrieval_file.id)  # Store uploaded file in session_state
                st.session_state.sent_files.add(file_identifier)

    if assistant_name != "Select Category":
        # Reset the conversation & starter questions, if the assistant has been changed
        if st.session_state.get("current_assistant") != assistant_name:
            st.session_state.messages = []
            st.session_state.current_assistant = assistant_name
        assistant_id = get_assistant_id(assistant_name)
        get_response(assistant_id)
            

# Call the main function to run the app
if __name__ == "__main__":
    main()
