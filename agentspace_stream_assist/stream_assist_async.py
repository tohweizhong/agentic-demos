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

import asyncio
import json
import os

project_id = "weizhong-project01"
location = "global"          # Values: "global", "us", "eu"
engine_id = "enterprise-search-17484208_1748420861365"
search_query = "roll a 20-side dice for me"

async def sample_stream_assist(
    project_id: str,
    location: str,
    engine_id: str,
    search_query: str,
):

    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    # Create a client
    client = discoveryengine_v1.AssistantServiceAsyncClient(client_options=client_options)
    # for i in client.parse_assistant_path(client.assistant_path()):
        # print(i)
    #print(client.transport)

    # Initialize request argument(s)
    request = discoveryengine_v1.StreamAssistRequest(
        query=discoveryengine_v1.types.Query(text=search_query),
        name=f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant",
    )

    # Make the request
    stream = await client.stream_assist(request=request)

    # Handle the response
    async for response in stream:
        print(response)

# [END discoveryengine_v1_generated_AssistantService_StreamAssist_async]

async def main():
    print("Querying discovery engine...")
    print(f"Search query: {search_query}")
    #output = sample_stream_assist(project_id, location, engine_id, search_query)
    #print(output)

   await sample_stream_assist(project_id, location, engine_id, search_query)

    # TODO
    # - get the session info
    # - continue the conversation
    # session_id = result.sessionInfo.session
    # print(session_id)

if __name__ == "__main__":
    asyncio.run(main())
