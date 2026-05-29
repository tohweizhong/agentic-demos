# 🏆 SharePoint File Agent Evaluation Report

Generated on: 2026-05-29 17:49:03 (APC Region/Vertex AI)

## 📊 Aggregate Metrics

| Metric | Score / Value |
| :--- | :--- |
| **Total Test Cases Executed** | 5 |
| **Semantic Accuracy Rate (LLM-as-a-Judge)** | `40.0%` 🟢 |
| **Tool Trajectory Match Rate** | `0.0%` 🎯 |
| **Average Latency Per Query** | `14.29s` ⚡ |

## 🔍 Individual Case Details

### Test Case #1: `PDF` (🔓 Unencrypted)
* **Source File**: `GovTech Products and Services Apr26/Accessibility/Accessibility _ Government Technology Agency of Singapore (GovTech Singapore).pdf`
* **Semantic Correctness**: ❌ | **Trajectory Match**: False ⚠️
* **Latency**: `7.85s` | **RMS Encrypted**: `False`

🗣️ **User Query**:
> What is Oobee and what is its primary function?

🎯 **Expected Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "Accessibility _ Government Technology Agency of Singapore (GovTech Singapore).pdf"
    }
  },
  {
    "tool": "read_sharepoint_file",
    "args": {
      "item_id": "01C6LRSEJ3Z2VB3UPPCFDIXS6WW7HIFNU4"
    }
  }
]
```

⚙️ **Actual Tool Trajectory**:
```json
[]
```

📄 **Expected Response**:
```text
Oobee is an open-source automated testing tool that scans and analyzes websites to identify code-level accessibility issues, aiming to improve accessibility for people with disabilities (PWD).
```

🤖 **Agent Actual Response**:
```text
I can't answer general knowledge questions. However, if you believe this information is contained within a SharePoint file, I can help you search for and read its contents. Please tell me what file or document I should look into.
```

---

### Test Case #2: `PDF` (🔓 Unencrypted)
* **Source File**: `GovTech Products and Services Apr26/Cybersecurity/Cybersecurity Capabilities _ Government Technology Agency of Singapore (GovTech Singapore).pdf`
* **Semantic Correctness**: ✅ | **Trajectory Match**: False ⚠️
* **Latency**: `12.91s` | **RMS Encrypted**: `False`

🗣️ **User Query**:
> According to the document, what percentage of local organisations in Singapore reported cyberattacks in 2023, and what percentage of those resorted to ransom payments?

🎯 **Expected Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "Cybersecurity Capabilities _ Government Technology Agency of Singapore (GovTech Singapore).pdf"
    }
  },
  {
    "tool": "read_sharepoint_file",
    "args": {
      "item_id": "01C6LRSEN4VCDJOOABBVGZG35S52ETZ2LN"
    }
  }
]
```

⚙️ **Actual Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "Singapore cyberattacks 2023"
    }
  },
  {
    "tool": "read_sharepoint_file",
    "args": {
      "item_id": "01C6LRSEN4VCDJOOABBVGZG35S52ETZ2LN",
      "drive_id": null
    }
  }
]
```

📄 **Expected Response**:
```text
In 2023, 84% of local organisations reported cyberattacks, with 53% resorting to ransom payments.
```

🤖 **Agent Actual Response**:
```text
According to the document "Cybersecurity Capabilities _ Government Technology Agency of Singapore (GovTech Singapore).pdf", in 2023, 84% of local organisations in Singapore reported cyberattacks, and 53% of those resorted to ransom payments.
```

---

### Test Case #3: `PDF` (🔓 Unencrypted)
* **Source File**: `GovTech Products and Services Apr26/Cybersecurity/Cybersecurity services _ Government Technology Agency of Singapore (GovTech Singapore).pdf`
* **Semantic Correctness**: ❌ | **Trajectory Match**: False ⚠️
* **Latency**: `21.93s` | **RMS Encrypted**: `False`

🗣️ **User Query**:
> When was the cybersecurity services page last updated?

🎯 **Expected Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "Cybersecurity services _ Government Technology Agency of Singapore (GovTech Singapore).pdf"
    }
  },
  {
    "tool": "read_sharepoint_file",
    "args": {
      "item_id": "01C6LRSENRX63FTYETSZELWGWXCUNPJR44"
    }
  }
]
```

⚙️ **Actual Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "cybersecurity services page"
    }
  }
]
```

📄 **Expected Response**:
```text
The cybersecurity services page was last updated on 31 July 2025.
```

🤖 **Agent Actual Response**:
```text
Here are the details for the "Cybersecurity services" page:

*   📄 **File Name**: [Cybersecurity services _ Government Technology Agency of Singapore (GovTech Singapore).pdf](https://weizhongt.sharepoint.com/sites/sharepoint-site-demo1/Shared%20Documents/GovTech%20Products%20and%20Services%20Apr26/Cybersecurity/Cybersecurity%20services%20_%20Government%20Technology%20Agency%20of%20Singapore%20(GovTech%20Singapore).pdf)
*   📁 **Relative Path**: `GovTech Products and Services Apr26/Cybersecurity/Cybersecurity services _ Government Technology Agency of Singapore (GovTech Singapore).pdf`
*   💾 **File Size**: `5.15 MB`
*   🔒 **Sensitivity**: `-`
*   📅 **Last Modified**: `2026-04-17 06:28`
*   🆔 **Unique ID**: `01C6LRSENRX63FTYETSZELWGWXCUNPJR44`
```

---

### Test Case #4: `PDF` (🔓 Unencrypted)
* **Source File**: `GovTech Products and Services Apr26/Cybersecurity/Cybersecurity_Playbook_for_Large_Language_Model_LLM_Applications.pdf`
* **Semantic Correctness**: ✅ | **Trajectory Match**: False ⚠️
* **Latency**: `19.65s` | **RMS Encrypted**: `False`

🗣️ **User Query**:
> Who developed the Cybersecurity Playbook for Large Language Model Applications?

🎯 **Expected Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "Cybersecurity_Playbook_for_Large_Language_Model_LLM_Applications.pdf"
    }
  },
  {
    "tool": "read_sharepoint_file",
    "args": {
      "item_id": "01C6LRSEKB6QCQTYLBS5EJ5VUNLBLJ4GBA"
    }
  }
]
```

⚙️ **Actual Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "Cybersecurity Playbook for Large Language Model Applications"
    }
  },
  {
    "tool": "read_sharepoint_file",
    "args": {
      "item_id": "01C6LRSEKB6QCQTYLBS5EJ5VUNLBLJ4GBA",
      "drive_id": null
    }
  }
]
```

📄 **Expected Response**:
```text
The Government Technology Agency (GovTech) developed the Cybersecurity Playbook for Large Language Model Applications.
```

🤖 **Agent Actual Response**:
```text
The Cybersecurity Playbook for Large Language Model Applications was developed by the **Government Technology Agency (GovTech)**.
```

---

### Test Case #5: `PDF` (🔓 Unencrypted)
* **Source File**: `GovTech Products and Services Apr26/Cybersecurity/GITSIR RFC 2350 Profile.pdf`
* **Semantic Correctness**: ❌ | **Trajectory Match**: False ⚠️
* **Latency**: `9.12s` | **RMS Encrypted**: `False`

🗣️ **User Query**:
> When was the GITSIR RFC 2350 Profile document last updated?

🎯 **Expected Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "GITSIR RFC 2350 Profile.pdf"
    }
  },
  {
    "tool": "read_sharepoint_file",
    "args": {
      "item_id": "01C6LRSEN6MLX2OKHTUJDKF6TAGUUXUDNQ"
    }
  }
]
```

⚙️ **Actual Tool Trajectory**:
```json
[
  {
    "tool": "search_sharepoint_files",
    "args": {
      "query": "GITSIR RFC 2350 Profile"
    }
  }
]
```

📄 **Expected Response**:
```text
The GITSIR RFC 2350 Profile document was last updated on 01 March 2023.
```

🤖 **Agent Actual Response**:
```text
The document "GITSIR RFC 2350 Profile.pdf" was last updated on 2026-04-17 06:28.
```

---

