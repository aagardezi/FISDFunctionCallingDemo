import time
import tempfile
import json
import streamlit as st
from streamlit_float import *
from streamlit_google_auth import Authenticate
from vertexai.generative_models import FunctionDeclaration, GenerativeModel, Tool, Part, FinishReason, SafetySetting
from google.cloud import bigquery
import google.auth
import logging


import helperbqfunction
import geminifunctionsbq

import geminifunctionfinhub
import helperfinhub







@st.dialog("Choose the Model")
def select_model():
    modelname = st.selectbox(
        "Select the Gemini version you would like to use",
        ("gemini-1.5-pro-002", "gemini-1.5-flash-002"),
        index=0,
        placeholder="Select a Model",
    )
    if st.button("Choose Model"):
        st.session_state.modelname = modelname
        st.rerun()


def get_project_id():
  """Gets the current GCP project ID.

  Returns:
    The project ID as a string.
  """

  try:
    _, project_id = google.auth.default()
    return project_id
  except google.auth.exceptions.DefaultCredentialsError as e:
    print(f"Error: Could not determine the project ID. {e}")
    return None

def handle_api_response(message_placeholder, api_requests_and_responses, backend_details):
    backend_details += "- Function call:\n"
    backend_details += (
                        "   - Function name: ```"
                        + str(api_requests_and_responses[-1][0])
                        + "```"
                    )
    backend_details += "\n\n"
    backend_details += (
                        "   - Function parameters: ```"
                        + str(api_requests_and_responses[-1][1])
                        + "```"
                    )
    backend_details += "\n\n"
    backend_details += (
                        "   - API response: ```"
                        + str(api_requests_and_responses[-1][2])
                        + "```"
                    )
    backend_details += "\n\n"
    with message_placeholder.container():
        st.markdown(backend_details)
    return backend_details

def handel_gemini_parallel_func(handle_api_response, response, message_placeholder, api_requests_and_responses, backend_details):
    logging.warning("Starting parallal function resonse loop")
    parts=[]
    for response in response.candidates[0].content.parts:
        logging.warning("Function loop starting")
        logging.warning(response)
        params = {}
        try:
            for key, value in response.function_call.args.items():
                params[key] = value
        except AttributeError:
            continue
                
        logging.warning("Prams processing done")
        logging.warning(response)
        logging.warning(response.function_call.name)
        logging.warning(params)

        function_name = response.function_call.name

        if function_name in helperbqfunction.function_handler.keys():
            api_response = helperbqfunction.function_handler[function_name](st.session_state.client, params)
            api_requests_and_responses.append(
                            [function_name, params, api_response]
                    )

        if function_name in helperfinhub.function_handler.keys():
            api_response = helperfinhub.function_handler[function_name](params)
            api_requests_and_responses.append(
                            [function_name, params, api_response]
                    )

        logging.warning("Function Response complete")

        logging.warning(api_response)

        parts.append(Part.from_function_response(
                    name=function_name,
                    response={
                        "content": api_response,
                    },
                    ),
                )

        backend_details = handle_api_response(message_placeholder, api_requests_and_responses, backend_details)

    logging.warning("Making gemin call for api response")

    response = st.session_state.chat.send_message(
                parts
            )
            
    logging.warning("gemini api response completed")
    return response,backend_details


def handle_gemini_serial_func(handle_api_response, response, message_placeholder, api_requests_and_responses, backend_details):
    response = response.candidates[0].content.parts[0]

    logging.warning(response)
    logging.warning("First Resonse done")

    function_calling_in_process = True
    while function_calling_in_process:
        try:
            logging.warning("Function loop starting")
            params = {}
            for key, value in response.function_call.args.items():
                params[key] = value
                    
            logging.warning("Prams processing done")
            logging.warning(response)
            logging.warning(response.function_call.name)
            logging.warning(params)

            function_name = response.function_call.name

            if function_name in helperbqfunction.function_handler.keys():
                logging.warning("BQ function found")
                api_response = helperbqfunction.function_handler[function_name](st.session_state.client, params)
                api_requests_and_responses.append(
                                [function_name, params, api_response]
                        )

            if function_name in helperfinhub.function_handler.keys():
                logging.warning("finhub function found")
                api_response = helperfinhub.function_handler[function_name](params)
                api_requests_and_responses.append(
                                [function_name, params, api_response]
                        )

            logging.warning("Function Response complete")

            logging.warning(api_response)
            logging.warning("Making gemin call for api response")

            response = st.session_state.chat.send_message(
                        Part.from_function_response(
                            name=function_name,
                            response={
                                "content": api_response,
                            },
                        ),
                    )

            logging.warning("Function Response complete")


            backend_details = handle_api_response(message_placeholder, api_requests_and_responses, backend_details)
                    
            logging.warning("gemini api response completed")
            logging.warning(response)
            logging.warning("next call ready")
            response = response.candidates[0].content.parts[0]


        except AttributeError:
            logging.warning(Exception)
            function_calling_in_process = False
    return response,backend_details



BIGQUERY_DATASET_ID = "lseg_data_normalised"
# PROJECT_ID = "genaillentsearch"
PROJECT_ID = get_project_id()

function_query_tool = Tool(
    function_declarations=[
        # geminifunctionsbq.list_datasets_func,
        # geminifunctionsbq.list_tables_func,
        # geminifunctionsbq.get_table_func,
        # geminifunctionsbq.sql_query_func,
        geminifunctionfinhub.symbol_lookup,
        #TODO: Add the other function for the LLM to call
        #These will access other fin hub api calls
    ],
)

generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}

safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
]



logging.warning("model name session state not initialised")
st.session_state.modelname = "gemini-1.5-pro-002"
# select_model()
# logging.warning(f"""In initialiser function model name is {st.session_state.modelname}""")

logging.warning("model name session state initialised")

st.title(f"""Company Agent: built using {st.session_state.modelname}""")

#TODO: Look at the system instruction below and see if it can be improved.
model = GenerativeModel(
    # "gemini-1.5-pro-002",
    st.session_state.modelname,
    system_instruction=[f"""You are a financial analyst that understands financial data. Do the analysis like and asset management investor and create a detaild report
                        lseg tick history data and uses RIC and ticker symbols to analyse stocks
                        When writing SQL query ensure you use the Date_Time field in the where clause. {PROJECT_ID}.{BIGQUERY_DATASET_ID}.lse_normalised table is the main trade table
                        RIC is the column to search for a stock
                        When accessing news use the symbol for the company instead of the RIC cod.
                        You can lookup the symbol using the symbol lookup function. Make sure to run the symbol_lookup before any subsequent functions.
                        When doing an analysis of the company, include the company profile, company news, company basic financials and an analysis of the peers
                        Also get the insider sentiment and add a section on that. Include a section on SEC filings."""],
    tools=[function_query_tool],
)

response=None


#Storing the Gemini response text in session state so on refresh it can be loaded back into the display
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

#Creating the Gemini calling class and storig it in session state
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat()

if "client" not in st.session_state:
    st.session_state.client = bigquery.Client(project="genaillentsearch")

#asking the user for input in the Chat message container 
if prompt := st.chat_input("What is up?"):

    #displaying the user input in the chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    
    #TODO: look at the prompt below see where it is being added to the user
    #input prompt and see if it can be improved
    prompt_enhancement = """ If the question requires SQL data then Make sure you get the data from the sql query first and then analyse it in its completeness if not get the news directly
            If the question relates to news use the stock symbol ticker and not the RIC code."""


    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""


        #GEMINI API CALL here
        response = st.session_state.chat.send_message(prompt + prompt_enhancement,generation_config=generation_config,
        safety_settings=safety_settings)
        logging.warning("This is the start")
        logging.warning(response)
        logging.warning("The start is done")

        logging.warning(f"""Length of functions is {len(response.candidates[0].content.parts)}""")

        api_requests_and_responses = []
        backend_details = ""
        api_response = ""

        # if len(response.candidates[0].content.parts) >1:
        #     response, backend_details = handel_gemini_parallel_func(handle_api_response, response, message_placeholder, api_requests_and_responses, backend_details)


        # else:
        #     response, backend_details = handle_gemini_serial_func(handle_api_response, response, message_placeholder, api_requests_and_responses, backend_details)

        #TODO: This code below is assuming that Gemini returns the functions in a seriel fashion
        #how would you improve it to handle parallel funciton calls
        #HINT: Look at the commented code above

        response = response.candidates[0].content.parts[0]

        logging.warning(response)
        logging.warning("First Resonse done")

        function_calling_in_process = True
        #This section handles the response from Gemini. The loop is to handle all the funciton calls
        #need to complete the action based on the users prompt
        while function_calling_in_process:
            #This try catch checks if the response is a function call and then handles it
            try:
                logging.warning("Function loop starting")
                params = {}
                for key, value in response.function_call.args.items():
                    params[key] = value
                        
                logging.warning("Prams processing done")
                logging.warning(response)
                logging.warning(response.function_call.name)
                logging.warning(params)

                #Get the function call evaluated by Gemini and call that function to complete part of the request.
                function_name = response.function_call.name

                if function_name in helperbqfunction.function_handler.keys():
                    logging.warning("BQ function found")
                    api_response = helperbqfunction.function_handler[function_name](st.session_state.client, params)
                    api_requests_and_responses.append(
                                    [function_name, params, api_response]
                            )

                if function_name in helperfinhub.function_handler.keys():
                    logging.warning("finhub function found")
                    api_response = helperfinhub.function_handler[function_name](params)
                    api_requests_and_responses.append(
                                    [function_name, params, api_response]
                            )

                logging.warning("Function Response complete")

                logging.warning(api_response)
                logging.warning("Making gemin call for api response")

                response = st.session_state.chat.send_message(
                            Part.from_function_response(
                                name=function_name,
                                response={
                                    "content": api_response,
                                },
                            ),
                        )

                logging.warning("Function Response complete")

                #This is to get the fucntion call output and format it to display in the UI
                backend_details = handle_api_response(message_placeholder, api_requests_and_responses, backend_details)
                        
                logging.warning("gemini api response completed")
                logging.warning(response)
                logging.warning("next call ready")
                response = response.candidates[0].content.parts[0]


            except AttributeError:
                logging.warning(Exception)
                function_calling_in_process = False

        time.sleep(3)

        #Gets the final response from Gemini and displays it with the intermediate funciton calls in the UI
        full_response = response.text
        with message_placeholder.container():
            st.markdown(full_response.replace("$", r"\$"))  # noqa: W605
            with st.expander("Function calls, parameters, and responses:"):
                st.markdown(backend_details)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": full_response,
                "backend_details": backend_details,
            }
        )
