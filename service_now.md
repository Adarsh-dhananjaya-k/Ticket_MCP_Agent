



# 🛠️ ServiceNow Configuration Guide: AI IT Service Desk

This guide outlines the required ServiceNow configurations to support the Python-based AI Teams Bot, including the custom API endpoints, token-based email approvals, and custom database fields.

## Step 1: Dictionary / Table Updates
The bot needs a place to store the AI's suggested engineer so the email notification script can highlight them. We also rely on the out-of-the-box (OOTB) `correlation_id` field to store the one-time security token.

1. Navigate to the **Incident (`incident`)** table dictionary.
2. Create a new field with the following details:
   * **Type:** Reference
   * **Reference Table:** User (`sys_user`)
   * **Column Label:** AI Suggested Engineer
   * **Column Name:** `u_ai_suggested_engineer`
3. **Note on `correlation_id`:** Ensure the OOTB `correlation_id` field exists and is active on the incident table. *You do not need to add it to the form layout; it is used purely in the backend.*

---

## Step 2: Create the Scripted REST API
We need a custom API to handle the handoff from Python and the unauthenticated clicks from the manager's email.

1. Navigate to **System Web Services > Scripted REST APIs**.
2. Create a new API:
   * **Name:** Teams Bot API
   * **API ID:** `teams_bot_api`
   * *(Note your API namespace, e.g., `1920142`. If it differs, update the `approval_url` in the Python `request_manager_approval` tool).*

### Resource A: Create Approval (POST)
This endpoint is called by the Python bot to inject the secure token and trigger the approval record.
* **Name:** Create Approval
* **HTTP Method:** POST
* **Relative Path:** `/create_approval`
* **Security:** `Requires authentication` (Checked ✅)
* **Script:**
```javascript
(function process(request, response) {
    try {
        var body = request.body.data;
        
        // 1. Save the secure token to the Incident
        if (body.approval_token && body.incident_sys_id) {
            var incGr = new GlideRecord('incident');
            if (incGr.get(body.incident_sys_id)) {
                incGr.correlation_id = body.approval_token; // Store one-time token
                incGr.update();
            }
        }

        // 2. Create the Approval Record
        var gr = new GlideRecord('sysapproval_approver');
        gr.initialize();
        gr.approver = body.manager_sys_id;
        gr.sysapproval = body.incident_sys_id;
        gr.source_table = 'incident'; 
        gr.document_id = body.incident_sys_id; 
        gr.state = 'requested';
        var newId = gr.insert();
        
        if (newId) {
            response.setStatus(201);
            response.setBody({"status": "success", "approval_sys_id": newId});
        } else {
            response.setStatus(500);
            response.setBody({"status": "error", "message": "Failed to insert approval record"});
        }
    } catch (e) {
        response.setStatus(500);
        response.setBody({"status": "error", "message": e.message});
    }
})(request, response);
```

### Resource B: Process Approval Click (GET)
This endpoint catches the manager's click from their email. It verifies the token and assigns the ticket.
* **Name:** Process Approval
* **HTTP Method:** GET
* **Relative Path:** `/process_approval`
* ⚠️ **Security:** `Requires authentication` (**UNCHECKED ❌**) - *Crucial so managers can click without logging in.*
* **Script:**
```javascript
(function process(request, response) {
    var token = request.queryParams.token[0];
    var incSysId = request.queryParams.incident_sys_id[0];
    var agentEmail = request.queryParams.agent[0];

    // 1. Validate the Token
    var incGr = new GlideRecord('incident');
    incGr.addQuery('sys_id', incSysId);
    incGr.addQuery('correlation_id', token); // Must match exactly
    incGr.query();

    response.setContentType('text/html');

    if (incGr.next()) {
        // TOKEN IS VALID
        var userGr = new GlideRecord('sys_user');
        userGr.get('email', agentEmail);
        
        // Update Incident
        incGr.assigned_to = userGr.sys_id;
        incGr.state = 2; // Move from On Hold (3) to In Progress (2)
        incGr.correlation_id = ''; // Clear token so link cannot be reused
        incGr.work_notes = "Assignment approved via email token. Assigned to: " + agentEmail;
        incGr.update();

        // Approve the sysapproval_approver record
        var appGr = new GlideRecord('sysapproval_approver');
        appGr.addQuery('sysapproval', incSysId);
        appGr.addQuery('state', 'requested');
        appGr.query();
        if (appGr.next()) {
            appGr.state = 'approved';
            appGr.update();
        }

        // Return Success HTML
        response.setStatus(200);
        response.getStreamWriter().writeString(
            "<div style='font-family: Arial; text-align: center; margin-top: 50px;'>" +
            "<h2>✅ Success!</h2>" +
            "<p>Ticket <b>" + incGr.number + "</b> has been successfully assigned to " + agentEmail + ".</p>" +
            "</div>"
        );
    } else {
        // INVALID OR EXPIRED TOKEN
        response.setStatus(403);
        response.getStreamWriter().writeString(
            "<div style='font-family: Arial; text-align: center; margin-top: 50px; color: red;'>" +
            "<h2>❌ Link Expired or Invalid</h2>" +
            "<p>This approval link has already been used or is invalid.</p>" +
            "</div>"
        );
    }
})(request, response);
```

---

## Step 3: Notification Email Script
This script dynamically queries the team workload, constructs the secure tokenized URLs, and formats the buttons.

1. Navigate to **System Notification > Email > Notification Email Scripts**.
2. Create a new script:
   * **Name:** `generate_manager_assignment_links`
   * **Script:**
```javascript
(function runMailScript(current, template, email, email_action, event) {
    var inc = current.sysapproval.getRefRecord();
    if (!inc || inc.sys_class_name != 'incident') return;

    var aiSuggested = inc.u_ai_suggested_engineer.getDisplayValue();
    var groupId = inc.assignment_group;
    
    // Base URL and Secure Token
    var instanceUrl = gs.getProperty('glide.servlet.uri');
    var secureToken = inc.correlation_id; 

    template.print("<p><b>AI Suggested Engineer:</b> " + (aiSuggested || "None specified") + "</p>");
    template.print("<h3>Current Team Workload:</h3><ul style='list-style-type: none; padding: 0;'>");

    var members =[];

    // Query team members
    var grMember = new GlideRecord('sys_user_grmember');
    grMember.addQuery('group', groupId);
    grMember.query();

    while (grMember.next()) {
        var userId = grMember.user.sys_id.toString();
        var userName = grMember.user.name.toString();
        var userEmail = grMember.user.email.toString(); 

        // Query active tickets
        var count = new GlideAggregate('incident');
        count.addQuery('active', 'true');
        count.addQuery('assigned_to', userId);
        count.addAggregate('COUNT');
        count.query();
        
        var activeTickets = 0;
        if (count.next()) {
            activeTickets = count.getAggregate('COUNT');
        }

        members.push({id: userId, name: userName, email: userEmail, count: activeTickets});
        template.print("<li style='margin-bottom: 5px;'><b>" + userName + "</b> &ndash; " + activeTickets + " active incidents</li>");
    }
    template.print("</ul><br/>");

    // Generate Tokenized Buttons
    template.print("<h3>Actions:</h3>");
    
    // NOTE: Update '1920142' in the URL below if your Scripted REST API namespace is different!
    for (var i = 0; i < members.length; i++) {
        var m = members[i];
        var actionUrl = instanceUrl + 
            "api/1920142/teams_bot_api/process_approval" +
            "?token=" + secureToken + 
            "&incident_sys_id=" + inc.sys_id + 
            "&agent=" + encodeURIComponent(m.email);

        var btnLabel = "[Assign " + m.name + "]";
        var btnStyle = "display:inline-block; padding:10px 15px; margin:5px 0; background-color:#e0e0e0; color:#333; text-decoration:none; border: 1px solid #ccc; border-radius:4px; font-weight: bold;";
        
        if (m.name == aiSuggested) {
            btnLabel = "⭐ Approve AI Assignment [" + m.name + "]";
            btnStyle = "display:inline-block; padding:10px 15px; margin:5px 0; background-color:#0056b3; color:white; text-decoration:none; border-radius:4px; font-weight: bold;";
        }

        template.print('<a href="' + actionUrl + '" style="' + btnStyle + '">' + btnLabel + '</a><br/>');
    }
    
    // Standard SNOW Link
    var navLink = instanceUrl + 'nav_to.do?uri=incident.do?sys_id=' + inc.sys_id;
    template.print('<br/><br/><p><a href="' + navLink + '" style="color:#0056b3; text-decoration:underline;">View Incident in ServiceNow</a></p>');

})(current, template, email, email_action, event);
```

---

## Step 4: System Notification
Finally, tie the email script to the actual email sent to the manager.

1. Navigate to **System Notification > Email > Notifications**.
2. Create or edit the notification:
   * **Name:** Manager Approval Request
   * **Table:** Approval (`sysapproval_approver`)
   * **When to send:** Record is inserted OR updated. State changes to `Requested`.
   * **Who will receive:** `Approver`
   * **What it will contain:**
      * **Subject:** `Approval Required for Incident ${sysapproval.number}`
      * **Message HTML:**
```html
Hello ${approver.name},<br/><br/>
A Critical Priority incident requires your assignment decision.<br/><br/>
<b>Incident Number:</b> ${sysapproval.number}<br/>
<b>Description:</b> ${sysapproval.short_description}<br/>
<b>Priority:</b> ${sysapproval.priority}<br/><br/>

${mail_script:generate_manager_assignment_links}
```