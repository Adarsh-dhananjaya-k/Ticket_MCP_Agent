import pandas as pd
from io import StringIO

DATA = """Name	Email	Team	Role	Workload	Manager	Manager_Email	Primary_Skills	Secondary_Skills	Skill_Domain	Expertise_Level
Alice	alice@demo.com	SAP_Support	L2	High	Mr. Kumar	adarshdhananjayak@gmail.com	SAP FI, SAP MM	SAP Incident Resolution	SAP ERP	Advanced
Bob	bob@demo.com	SAP_Support	L2	Low	Mr. Kumar	adarshdhananjayak@gmail.com	SAP UI	SAP Ticket Handling	SAP ERP	Intermediate
Charlie	charlie@demo.com	Database_Admin	L3	Medium	Ms. Sharma	sharma@demo.com	PostgreSQL, Oracle	Database Optimization	Database	Expert
David	david@demo.com	Network_Ops	L1	Low	Mr. Patel	patel@demo.com	Network Monitoring	LAN Troubleshooting	Network	Beginner
Eve	eve@demo.com	Network_Ops	L2	Low	Mr. Patel	patel@demo.com	Firewall Configuration	VPN Setup	Network	Intermediate
Frank	frank@demo.com	Network_Ops	L1	Medium	Mr. Patel	patel@demo.com	LAN Support	Network Monitoring	Network	Intermediate
Grace	grace@demo.com	Database_Admin	L2	Low	Ms. Sharma	sharma@demo.com	MySQL	Backup & Recovery	Database	Intermediate
Henry	henry@demo.com	Database_Admin	L1	Medium	Ms. Sharma	sharma@demo.com	SQL Queries	Database Monitoring	Database	Beginner
Irene	irene@demo.com	SAP_Support	L1	Low	Mr. Kumar	adarshdhananjayak@gmail.com	SAP Ticket Handling	SAP User Support	SAP ERP	Beginner
Jack	adarshsurekha@gmail.com	SAP_Support	L1	Low	Mr. Kumar	adarshdhananjayak@gmail.com	SAP UI/UX, SAP Fiori	Frontend SAP Apps	SAP ERP	Advanced
Karen	vijethfernandes23@gmail.com	Software_Support	L1	Low	Ms. Nair	vijethfernandes21@gmail.com	UI/UX Design	React, HTML, CSS	Frontend	Advanced
Leo	leo@demo.com	Software_Support	L1	Medium	Ms. Nair	vijethfernandes21@gmail.com	JavaScript	Web Bug Fixing	Frontend	Intermediate
Mia	mia@demo.com	Software_Support	L2	Low	Ms. Nair	vijethfernandes21@gmail.com	Python	Backend API Support	Backend	Intermediate
Nathan	nathan@demo.com	Software_Support	L2	High	Ms. Nair	vijethfernandes21@gmail.com	Java Backend	Microservices Debugging	Backend	Advanced
Olivia	olivia@demo.com	Software_Support	L3	Medium	Ms. Nair	vijethfernandes21@gmail.com	System Architecture	Backend Optimization	Software Architecture	Expert
Paul	paul@demo.com	Hardware_Support	L1	Low	Mr. Verma	verma@demo.com	Desktop Setup	Hardware Troubleshooting	Hardware	Beginner
Quinn	quinn@demo.com	Hardware_Support	L1	High	Mr. Verma	verma@demo.com	Laptop Repair	Peripheral Setup	Hardware	Intermediate
Rachel	rachel@demo.com	Hardware_Support	L2	Low	Mr. Verma	verma@demo.com	Hardware Diagnostics	Device Drivers	Hardware	Intermediate
Sam	sam@demo.com	Hardware_Support	L2	Medium	Mr. Verma	verma@demo.com	Hardware Maintenance	System Imaging	Hardware	Intermediate
Tina	tina@demo.com	Hardware_Support	L3	Low	Mr. Verma	verma@demo.com	Server Hardware	Infrastructure Troubleshooting	Hardware	Expert
Uma	uma@demo.com	Cloud_Ops	L1	Low	Mr. Reddy	reddy@demo.com	AWS Basics	Cloud Monitoring	Cloud	Beginner
Victor	victor@demo.com	Cloud_Ops	L1	Medium	Mr. Reddy	reddy@demo.com	Azure Support	Cloud Ticket Handling	Cloud	Intermediate
Wendy	wendy@demo.com	Cloud_Ops	L2	Low	Mr. Reddy	reddy@demo.com	AWS EC2	Cloud Deployment	Cloud	Intermediate
Xander	xander@demo.com	Cloud_Ops	L2	High	Mr. Reddy	reddy@demo.com	Kubernetes	Docker Containers	Cloud DevOps	Advanced
Yara	yara@demo.com	Cloud_Ops	L3	Medium	Mr. Reddy	reddy@demo.com	Cloud Architecture	Multi-Cloud Infrastructure	Cloud	Expert
Zoe	zoe@demo.com	Cloud_Ops	L3	Low	Mr. Reddy	reddy@demo.com	Cloud Security	IAM Policies	Cloud	Advanced
Jhon	jhon@demo.com	Procurement	L3	Low	Mr. Tom	tom@demo.com	Vendor Management	Purchase Orders	Procurement	Advanced
"""

# Convert text data to DataFrame
df = pd.read_csv(StringIO(DATA), sep="\t")

# Save to Excel
df.to_excel("roster_with_skills.xlsx", index=False)

print("Excel file 'roster_with_skills.xlsx' created successfully!")