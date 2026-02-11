# -*- coding: utf-8 -*-
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Generated code. DO NOT EDIT!
#
# Snippet for StreamAssist
# NOTE: This snippet has been automatically generated for illustrative purposes only.
# It may require modifications to work in your environment.

# To install the latest published package dependency, execute the following:
#   python3 -m pip install google-cloud-discoveryengine


# [START discoveryengine_v1_generated_AssistantService_StreamAssist_async]
# This snippet has been automatically generated and should be regarded as a
# code template only.
# It will require modifications to work:
# - It may require correct/in-range values for request initialization.
# - It may require specifying regional endpoints when creating the service
#   client as shown in:
#   https://googleapis.dev/python/google-api-core/latest/client_options.html

from google.cloud import discoveryengine_v1
from google.api_core.client_options import ClientOptions

# Update accordingly
project_id = "weizhong-project01"
location = "global"          # Values: "global", "us", "eu"
engine_id = "enterprise-search-17484208_1748420861365"
search_query = "tell me about dyson singapore"
another_search_query = "what is their address?"
last_search_query = "how can i get there from google singapore?"

def sample_stream_assist(
    project_id: str,
    location: str,
    engine_id: str,
    search_query: str,
    session_id=None,
):
    # Client options
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    # Create a client
    client = discoveryengine_v1.AssistantServiceClient(client_options=client_options)

    # Check is session_id is present
    if session_id is None:
        # Initialize request argument(s)
        request = discoveryengine_v1.StreamAssistRequest(
            name=f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant",
            query=discoveryengine_v1.types.Query(text=search_query),
        )

        # Make the request
        stream = client.stream_assist(request=request)

        # Handle the response
        for response in stream:
            #print(response)
            return_value = response
        
        return return_value # This contains the session_info

    # With Session ID
    else:
        #print(search_query)
        request = discoveryengine_v1.StreamAssistRequest(
            name=f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant",
            query=discoveryengine_v1.types.Query(text=search_query),
            session=session_id,
        )
        stream = client.stream_assist(request=request)
        
        for response in stream:
            #print(response)
            return_value = response
        
        return return_value 

def main():
    print("Querying discovery engine...")
    print(f"First search query: {search_query}")
    result = sample_stream_assist(project_id, location, engine_id, search_query)

    # Get the session info
    # Continue the conversation
    session_id = result.session_info.session
    print(f"Session ID: {session_id}")

    # Run sample_stream_assist again
    print(f"Second search query: {another_search_query}")
    result2 = sample_stream_assist(project_id, location, engine_id, another_search_query, session_id=session_id)

    # Run sample_stream_assist last time
    print(f"Last search query: {last_search_query}")
    result3 = sample_stream_assist(project_id, location, engine_id, last_search_query, session_id=session_id)

if __name__ == "__main__":
   main()
