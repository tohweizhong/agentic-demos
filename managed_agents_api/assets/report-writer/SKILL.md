---
name: report-writer
description: Writes a short Markdown sales report with a fixed structure. Use when the user asks for a report about the sales data.
---

# Report writer

Write the report in Markdown. Use this structure, in this order:

1. `# Sales report: <period>`
2. `## Summary`: three to five bullet points. Put the most important fact first.
3. `## Key numbers`: a table with the metric, the value, and the change from the previous period.
4. `## Charts`: one line for each chart, with a Markdown image link to the PNG file.
5. `## Method`: two or three sentences. Say which file you read and how you calculated the numbers.
6. `## Limits`: say that the data is synthetic.

Rules:

- Round money to whole numbers. Round percentages to one decimal place.
- Use the active voice. Use short sentences.
- Do not put numbers in the report that you did not calculate from the file.
