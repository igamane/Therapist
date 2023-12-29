import os
import openai
import time
import streamlit as st
from dotenv import load_dotenv
import time
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE


# Load environment variables from .env file
load_dotenv()

# Load the Word document using the absolute path
doc = Document("The-Achilles-Guide-to-the-Galaxy-aka-Communication-Passport.docx")

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Create a client instance
client = openai.Client()

# %%%%%%%%%%%%%%%%%% Document Updating Functions %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def add_paragraph_after_header(header_text, new_paragraph):
    found_header = False
    for idx, paragraph in enumerate(doc.paragraphs):
        if header_text in paragraph.text:
            found_header = True
        elif found_header:
            doc.paragraphs[idx].insert_paragraph_before(new_paragraph)
            # Add a paragraph with no text after the table to create space
            doc.add_paragraph()
            doc.save('The-Achilles-Guide-to-the-Galaxy-aka-Communication-Passport.docx')
            return f"Document update: the paragraph has been added after the header'{header_text}' - tell the user what you have added"

    if not found_header:
        return f"Header '{header_text}' not found in the document."
  
def add_row_to_table_by_index(table_index, row_data):
    total_tables = len(doc.tables)

    if table_index < 0 or table_index >= total_tables:
        return f"Table index '{table_index}' is out of range."

    table = doc.tables[table_index]

    # Add a row to the table with the specified data
    new_row = table.add_row().cells
    for i, cell_data in enumerate(row_data):
        new_row[i].text = str(cell_data)
    doc.save('The-Achilles-Guide-to-the-Galaxy-aka-Communication-Passport.docx')
    return "Document update: row has been added to the table - tell the user what you have added"


def create_new_table(data):
    num_rows = len(data)
    if num_rows == 0:
        return "No data provided."

    num_cols = len(data[0])

    # Add a table to the document based on the size of the data
    table = doc.add_table(rows=num_rows, cols=num_cols)

    # Retrieve the style of the previous table if it exists
    if len(doc.tables) > 1:  # Assuming the previous table is at index 0
        previous_table_style = doc.tables[0].style
        table.style = previous_table_style.name  # Apply the style to the new table

    # Insert values into the cells of the table
    for i in range(num_rows):
        for j in range(num_cols):
            cell = table.cell(i, j)
            cell.text = str(data[i][j])  # Set the text for each cell

    # Add a paragraph with no text after the table to create space
    doc.add_paragraph()
    doc.save('The-Achilles-Guide-to-the-Galaxy-aka-Communication-Passport.docx')

    return "Document update: table has been created - tell the user the table content"


def add_new_section(header_text, section_content):
    # Check if 'Heading 1' style exists in the document
    styles = doc.styles
    heading_style_exists = any(style.name == 'Heading 1' and style.type == WD_STYLE_TYPE.PARAGRAPH for style in styles)

    # If 'Heading 1' style doesn't exist, create it
    if not heading_style_exists:
        style = doc.styles.add_style('Heading 1', WD_STYLE_TYPE.PARAGRAPH)
        font = style.font
        font.bold = True
        font.size = Pt(16)

    # Add a heading with the specified text using the 'Heading 1' style
    doc.add_heading(header_text, level=1)

    # Check if '**' exists in the section_content
    if '**' not in section_content:
        # If '**' is not present, add the entire section as regular text
        doc.add_paragraph(section_content)
    else:
        # Split the section content by '**'
        sections = section_content.split('**')

        # Add content for the new section
        for i, text in enumerate(sections):
            p = doc.add_paragraph()
            if i % 2 == 0:
                # Non-bold text
                p.add_run(text)
            else:
                # Bold text
                run = p.add_run(text)
                run.font.bold = True

    # Add a paragraph with no text after the table to create space
    doc.add_paragraph()
    doc.save('The-Achilles-Guide-to-the-Galaxy-aka-Communication-Passport.docx')

    return "Document update: new section has been added - tell the user what you have added"

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
    
    # Define a dispatch table
    function_dispatch_table = {
        "add_paragraph_after_header": add_paragraph_after_header,
        "add_row_to_table_by_index": add_row_to_table_by_index,
        "create_new_table": create_new_table,
        "add_new_section": add_new_section
    }

    while True:
        # Wait for 5 seconds
        time.sleep(5)

        # Retrieve the run status
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        print(run_status.status)
        # If run is completed, get messages
        if run_status.status == 'completed':
            break
        elif run_status.status == 'requires_action':
            required_actions = run_status.required_action.submit_tool_outputs.model_dump()
            tool_outputs = []
            import json
            for action in required_actions["tool_calls"]:
                func_name = action['function']['name']
                arguments = json.loads(action['function']['arguments'])
                print(func_name)
                print(arguments)
                print("999999999999999")

                func = function_dispatch_table.get(func_name)

                if func:
                    result = func(**arguments)
                    # Ensure the output is a JSON string
                    output = json.dumps(result) if not isinstance(result, str) else result
                    print(output)
                    tool_outputs.append({
                        "tool_call_id": action["id"],
                        "output": output
                    })
                else:
                    print(f"Function {func_name} not found")
            
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
        else:
            time.sleep(5)

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

    # Add download button for myfile.csv
    with open('The-Achilles-Guide-to-the-Galaxy-aka-Communication-Passport.docx', 'rb') as f:
        st.sidebar.download_button('Download The Updated Achilles Guide', f, file_name='The-Achilles-Guide-to-the-Galaxy-aka-Communication-Passport.docx', mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
   

# Call the main function to run the app
if __name__ == "__main__":
    main()
