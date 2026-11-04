# Power Automate flow: setup notes

**Status: not yet built in Power Automate.** The flow needs your Microsoft sign-in, so it was designed and written down here but has not been run. Until you build it, do not claim Power Automate in the README, resume or demo; the clearly labelled **fallback approval page** (`/review`) does the same job and logs decisions with `channel = fallback_page`.

## What the flow does

```
Every 15 minutes
  -> HTTP GET  {base}/cases?status=pending_review      (X-API-Key header)
  -> For each case (one at a time):
       Start and wait for an approval  (Approvals connector: email + Teams + Power Automate app)
         options: Approve | Approve with edits | Reject
         details: AI summary, confidence label, fact check failures, link to /review
       Compose: Approve -> approve, Approve with edits -> edit, Reject -> reject
       HTTP POST {base}/cases/{case_id}/decision
         { decision, reviewer = responder's name, comment, edited_summary = comment if edit,
           channel = "power_automate" }
```

The API stores the reviewer, decision and UTC time in the `decisions` table. Nothing is filed or sent anywhere else.

## Before you start

1. **Licence check.** The *HTTP* action is a **premium** connector. A Microsoft 365 work/school account usually needs a Power Automate Premium licence or the free **Developer Plan** (https://aka.ms/PowerAppsDevPlan). The Approvals connector is standard. If you cannot get premium, use the fallback page and say so.
2. **Make the local API reachable.** Power Automate runs in the cloud, so it cannot call `localhost`. Run the API and expose it with a tunnel, for example:
   ```
   uvicorn api.main:app --port 8000
   devtunnel host -p 8000 --allow-anonymous     # or: ngrok http 8000
   ```
   Set `FRAUDFLOW_API_KEY` in `.env` first so the tunnel is not open to anyone. Only synthetic data is served.

## Build it (about 15 minutes)

1. Go to https://make.powerautomate.com > **Create** > **Scheduled cloud flow**, name it `FraudFlow review`, repeat every 15 minutes.
2. **+ New step > HTTP**: Method `GET`, URI `https://<your-tunnel>/cases?status=pending_review&limit=10`, header `X-API-Key: <your key>`. Rename it `Get pending cases`.
3. **+ New step > Apply to each**, input: `Body` of *Get pending cases*. In settings set concurrency to 1.
4. Inside it, **Approvals > Start and wait for an approval**:
   * Approval type: **Custom Responses - Wait for one response**; responses: `Approve`, `Approve with edits`, `Reject`
   * Title: `FraudFlow case ` + `items('Apply_to_each')?['case_id']` + ` - ` + `items('Apply_to_each')?['label']`
   * Assigned to: your email
   * Details: the expressions shown in `flow_definition.json` (summary, confidence, check failures) and a note that edits go in the comment box
   * Item link: `https://<your-tunnel>/review`
5. **Compose** named `Pick decision`, expression:
   `if(equals(outputs('Start_and_wait_for_an_approval')?['body/outcome'],'Approve'),'approve',if(equals(outputs('Start_and_wait_for_an_approval')?['body/outcome'],'Approve with edits'),'edit','reject'))`
6. **HTTP** named `Post decision to FraudFlow`: Method `POST`, URI `https://<your-tunnel>/cases/` + `case_id` + `/decision`, headers `X-API-Key` and `Content-Type: application/json`, body as in `flow_definition.json`.
7. Save, then **Test > Manually**. Approve one case in Outlook/Teams, and check `GET /decisions` shows your name and `channel: power_automate`.

## After it works

* Export it: **My flows > ... > Export > Package (.zip)** and save as `flow/FraudFlow_review_export.zip`; replace the hand-written `flow_definition.json` note.
* Take screenshots (flow designer, the approval email/Teams card, a run history) into `flow/screenshots/`.
* Only then change the README status line to "Power Automate flow: built and tested".

## Proof the API side works today

`python -m flow.smoke_test` starts the API on a **copy** of the database and plays the flow's two HTTP calls (GET cases, POST a decision) end to end. It labels its decision `reviewer = "smoke test (automated, not a real review)"` so it can never be mistaken for a human decision, and it writes `flow/smoke_test_log.md`. It is a test of the plumbing, not of Power Automate.
