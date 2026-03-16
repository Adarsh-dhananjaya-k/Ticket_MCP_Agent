

### How to Trigger Proactive Messages via Business Rule Script

We are going to create an **Async Business Rule**. We use "Async" instead of "After" so that when the IT Agent clicks "Resolve", their screen doesn't freeze while ServiceNow waits for your Python server to reply!

#### Step 1: Create the Business Rule
1. In ServiceNow, navigate to **System Definition > Business Rules**.
2. Click **New**.
3. **Name:** `Notify Teams on Resolve`
4. **Table:** Incident (`incident`)
5. Check the **Advanced** checkbox (this reveals the scripting tab).

#### Step 2: Set the Trigger Conditions
1. Go to the **When to run** tab.
2. **When:** `async` *(Very important!)*
3. **Insert:** Unchecked
4. **Update:** Checked ✅
5. **Filter Conditions:** 
   * `State` `changes to` `Resolved`

#### Step 3: Write the Script
1. Go to the **Advanced** tab.
2. Paste this exact JavaScript into the script block. Make sure to replace `YOUR_NGROK_URL` with your actual Python server address!

```javascript
(function executeRule(current, previous /*null when async*/) {
    try {
        // 1. Check if the Caller actually has an email address
        var callerEmail = current.caller_id.email.toString();
        if (!callerEmail) {
            gs.info("Teams Notify: Skipped. Caller has no email.");
            return;
        }

        // 2. Prepare the REST Request to Python
        var request = new sn_ws.RESTMessageV2();
        
        // ⚠️ UPDATE THIS URL TO YOUR PYTHON SERVER (e.g., ngrok)
        request.setEndpoint('https://YOUR_NGROK_URL.ngrok.app/api/notify'); 
        request.setHttpMethod('POST');
        request.setRequestHeader("Accept", "application/json");
        request.setRequestHeader("Content-Type", "application/json");

        // 3. Gather ticket details
        var ticketNumber = current.number.toString();
        
        // Safely get the name of who resolved it (fallback to the updater)
        var resolvedBy = "";
        if (!current.resolved_by.nil()) {
            resolvedBy = current.resolved_by.name.toString();
        } else {
            resolvedBy = current.sys_updated_by.toString();
        }

        // 4. Build the JSON Payload
        var body = {
            "user_email": callerEmail,
            "message": "✅ **Good news!** Ticket " + ticketNumber + " has just been resolved by " + resolvedBy + ". \n\n**Resolution Notes:** " + current.close_notes + "\n\nIs your issue completely fixed?"
        };
        
        request.setRequestBody(JSON.stringify(body));

        // 5. Fire the request!
        var response = request.execute();
        var httpResponseStatus = response.getStatusCode();
        
        gs.info("Teams Proactive Notify fired for " + ticketNumber + ". HTTP Status: " + httpResponseStatus);

    } catch (ex) {
        gs.error("Teams Proactive Notify Error: " + ex.message);
    }
})(current, previous);
```

### Why this Scripted approach is awesome:
1. **Dynamic Messaging:** I added `current.close_notes` into the script! Now, when the bot pings the user, it will say: *"Good news! Ticket INC0010154 was resolved by Karen User. Resolution Notes: Rebooted the server. Is your issue fixed?"*
2. **Fail-Safe:** Wrapping it in a `try/catch` ensures that if your Python server is turned off, ServiceNow doesn't crash or show an error to the IT agent. It just quietly logs the error in the background.

Once you save this Business Rule, and you have the Python `/api/notify` endpoint running from my previous message, your bot will be fully proactive!