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

import logging
from typing import Any
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def get_onboarding_tasks(tool_context: ToolContext) -> str:
    """Retrieves the list of onboarding tasks for the current employee and their completion status.

    Args:
        tool_context: The injected execution context containing session state.

    Returns:
        A formatted text showing all tasks and their current statuses.
    """
    tasks = tool_context.state.get("tasks", {})
    if not tasks:
        return "No onboarding tasks have been initialized yet."

    lines = ["Here are your onboarding tasks:"]
    for task, status in tasks.items():
        status_emoji = "✅" if status == "COMPLETED" else "⏳"
        lines.append(f"- [{status_emoji}] {task}: {status}")
    return "\n".join(lines)


def complete_onboarding_task(task_name: str, tool_context: ToolContext) -> str:
    """Marks a specific onboarding task as completed.

    Args:
        task_name: The exact name of the task to complete.
        tool_context: The injected execution context containing session state.

    Returns:
        A confirmation message indicating whether the task was updated successfully.
    """
    tasks = tool_context.state.get("tasks", {})
    if not tasks:
        return "No onboarding tasks found to complete."

    # Look for fuzzy matching
    matched_task = None
    for t in tasks:
        if task_name.lower().strip() in t.lower().strip():
            matched_task = t
            break

    if not matched_task:
        return f"Task '{task_name}' not found. Please refer to get_onboarding_tasks to view valid tasks."

    if tasks[matched_task] == "COMPLETED":
        return f"Task '{matched_task}' is already completed."

    tasks[matched_task] = "COMPLETED"
    tool_context.state.update({"tasks": tasks})
    return f"Success! Onboarding task '{matched_task}' has been marked as COMPLETED."


def submit_payroll_details(
    bank_name: str,
    account_number: str,
    routing_number: str,
    tool_context: ToolContext,
) -> str:
    """Submits the employee's payroll direct deposit bank details and automatically completes the payroll task.

    Args:
        bank_name: The name of the bank.
        account_number: The bank account number.
        routing_number: The bank routing number.
        tool_context: The injected execution context containing session state.

    Returns:
        A success message confirming the details were saved and the payroll task was completed.
    """
    # TODO(security): PII Masking applied to credit card/bank details when logging.
    # We do not log full account numbers.
    masked_acc = f"******{account_number[-4:]}" if len(account_number) >= 4 else "****"
    logger.info(f"Submitting payroll bank details: bank={bank_name}, account={masked_acc}")

    # Save details
    payroll_info = {
        "bank_name": bank_name,
        "account_number": account_number,
        "routing_number": routing_number,
    }
    tool_context.state.update({"payroll_details": payroll_info})

    # Complete task
    tasks = tool_context.state.get("tasks", {})
    payroll_task = "Submit Payroll Direct Deposit Details"
    if payroll_task in tasks:
        tasks[payroll_task] = "COMPLETED"
        tool_context.state.update({"tasks": tasks})

    return f"Successfully saved payroll details for {bank_name} (Account Ending in {account_number[-4:] if len(account_number)>=4 else ''}). The task 'Submit Payroll Direct Deposit Details' is now marked as COMPLETED."


def submit_emergency_contact(
    contact_name: str,
    phone_number: str,
    relationship: str,
    tool_context: ToolContext,
) -> str:
    """Submits the employee's emergency contact information and automatically completes the emergency contact task.

    Args:
        contact_name: The full name of the emergency contact person.
        phone_number: The phone number of the contact person.
        relationship: The relationship to the employee (e.g. spouse, parent).
        tool_context: The injected execution context containing session state.

    Returns:
        A success message confirming the contact details were saved and the emergency contact task was completed.
    """
    logger.info(f"Submitting emergency contact: name={contact_name}, relationship={relationship}")

    contact_info = {
        "contact_name": contact_name,
        "phone_number": phone_number,
        "relationship": relationship,
    }
    tool_context.state.update({"emergency_contact": contact_info})

    # Complete task
    tasks = tool_context.state.get("tasks", {})
    emergency_task = "Fill Emergency Contact Form"
    if emergency_task in tasks:
        tasks[emergency_task] = "COMPLETED"
        tool_context.state.update({"tasks": tasks})

    return f"Successfully saved emergency contact: {contact_name} ({relationship}). The task 'Fill Emergency Contact Form' is now marked as COMPLETED."


def get_company_policy_info(topic: str) -> str:
    """Retrieves information on standard company onboarding policies (e.g. office hours, dress code, benefits, holidays).

    Args:
        topic: The topic of interest, e.g., 'working hours', 'benefits', 'holidays', 'dress code'.

    Returns:
        A string containing details about the requested company policy.
    """
    topic_clean = topic.lower().strip()
    
    policies = {
        "working hours": (
            "Standard company working hours are 9:00 AM to 6:00 PM, Monday through Friday. "
            "Some teams support flexible work hours or core collaboration hours from 10:00 AM to 4:00 PM."
        ),
        "dress code": (
            "Our company dress code is business casual. "
            "Dress comfortably but professionally. Jeans are acceptable if neat and without tears."
        ),
        "benefits": (
            "We offer comprehensive health, dental, and vision insurance starting on your first day. "
            "We also provide a 401(k) retirement matching program (up to 4% matching) and wellness benefits."
        ),
        "holidays": (
            "We observe 11 standard company holidays including New Year's Day, Memorial Day, "
            "Independence Day, Labor Day, Thanksgiving (Thursday & Friday), and Christmas Day. "
            "You also receive 20 days of Paid Time Off (PTO) annually, accrued monthly."
        )
    }

    # Search for matching policy keyword
    for key, value in policies.items():
        if key in topic_clean or topic_clean in key:
            return value

    # Default fallback
    return (
        f"I don't have specific policy information on '{topic}'. "
        "Standard company policies can be found in section 3 of the Employee Handbook. "
        "Available topics I can answer directly: 'working hours', 'dress code', 'benefits', 'holidays'."
    )
