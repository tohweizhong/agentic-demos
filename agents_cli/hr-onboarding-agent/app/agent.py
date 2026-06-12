# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.onboarding_tools import (
    get_onboarding_tasks,
    complete_onboarding_task,
    submit_payroll_details,
    submit_emergency_contact,
    get_company_policy_info,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a friendly and professional HR Onboarding Assistant. "
        "Your goal is to guide new employees through their company onboarding process. "
        "Use the tools provided to check their tasks, submit payroll bank details, "
        "submit emergency contact details, complete tasks, or retrieve company policy info. "
        "Be helpful, welcoming, and ensure all onboarding tasks are successfully completed. "
        "Always refer to the employee by their name once it is known (you can check the state or ask)."
    ),
    tools=[
        get_onboarding_tasks,
        complete_onboarding_task,
        submit_payroll_details,
        submit_emergency_contact,
        get_company_policy_info,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)

