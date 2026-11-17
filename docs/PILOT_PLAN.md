# Controlled pilot plan

Reference: proposal sections 3.4 and 6. This pilot has not been run.

Use a separate staging or demonstration database with fictional/private test
records, one beneficiary, one approved donor, NGO staff, and an administrator.
Prepare an equivalent phone/message coordination scenario for comparison.

## Tasks and acceptance

| Scenario | Tasks | Evidence to retain |
| --- | --- | --- |
| Ordinary relief request | Beneficiary submits; staff verifies; donor pledges; staff assigns; responder delivers; beneficiary confirms receipt | Reference, six status events, first-action time, confirmation record |
| More information | Staff asks a question; beneficiary responds; staff reviews again | All review records; first acknowledgement unchanged |
| Rejected request | Staff records a justified rejection | Retained decision; no donor visibility or assignment |
| Anonymous entry | Submit without an account; staff coordinates and records the recipient's phone confirmation | Reachable contact in private workspace; public reference; authorized closure |
| Approval boundary | Register a new donor; attempt support before approval; administrator approves | Denied action before approval; successful offer afterward |
| Invalid action | Try to skip delivery stages, omit confirmation, or use another user's record | Clear denial/validation; no partial status or delivery records |
| Dependency failure | Disable/block maps; check the area list, submission, review, and delivery | Core workflow completes without maps; private information remains hidden |
| Small screen/slow connection | Repeat the key tasks on a physical low-to-mid range phone and a slow connection | Device/browser, completion time, interface issues, successful recovery |

## Measurements

Record these values per participant/scenario. Keep collected feedback free of
unnecessary personal information.

| Field | Definition |
| --- | --- |
| Scenario/role/device | Task identifier, participant role, browser and screen/device |
| Task start/end | Wall-clock task timestamps |
| Completion | Successful, failed, or completed with assistance |
| Validation errors | Required-field errors encountered before submission |
| Workflow errors | Incorrect/denied status actions, retries, or lost updates |
| Request submission | The stored `submitted_at` timestamp |
| First staff action | The stored `acknowledged_at` timestamp |
| Acknowledgement minutes | `(acknowledged_at - submitted_at)` in minutes |
| Delivery confirmation | Whether delivered support has recipient confirmation |
| Clarity rating | Participant answer on a 1-5 scale |
| Coordination steps | Count of manual contacts/steps in the prototype and baseline |
| Feedback | One concise observation or improvement suggestion |

Evaluate the median acknowledgement time against the proposal's **less than two
hours** target. Also report validation success, task-completion rate/time,
workflow errors, recipient-confirmation coverage, clarity ratings, and manual
coordination steps. Count delivered records in the coverage denominator;
undelivered pledges are not completed support.

Report the participant count and test conditions alongside the results.
Development seed timestamps and automated execution times do not establish
pilot performance.

## After the pilot

Append a new consecutive entry to `PROJECT_PROGRESS.md`, retain the measured
results in the final report, fix observed defects, and repeat the affected
scenarios. Use the proposal's week-12 buffer for refinement and presentation.
