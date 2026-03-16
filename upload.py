import pandas as pd
from io import StringIO

DATA = """Name	Email	Team	Role	Workload	Manager	Manager_Email	Skills
Alice	alice@demo.com	SAP_Support	L2	High	Mr. Kumar	kumar@demo.com	Medium
Bob	bob@demo.com	SAP_Support	L2	Low	Mr. Kumar	kumar@demo.com	Low
Charlie	charlie@demo.com	Database_Admin	L3	Medium	Ms. Sharma	sharma@demo.com	High
David	david@demo.com	Network_Ops	L1	Low	Mr. Patel	patel@demo.com	Low
Eve	eve@demo.com	Network_Ops	L2	Low	Mr. Patel	patel@demo.com	Medium
Frank	frank@demo.com	Network_Ops	L1	Medium	Mr. Patel	patel@demo.com	Medium
Grace	grace@demo.com	Database_Admin	L2	Low	Ms. Sharma	sharma@demo.com	Medium
Henry	henry@demo.com	Database_Admin	L1	Medium	Ms. Sharma	sharma@demo.com	Low
Irene	irene@demo.com	SAP_Support	L1	Low	Mr. Kumar	kumar@demo.com	Low
Jack	jack@demo.com	SAP_Support	L3	Medium	Mr. Kumar	kumar@demo.com	High
Karen	vijethfernandes23@gmail.com	Software_Support	L1	Low	Ms. Nair	vijethfernandes21@gmail.com	High
Leo	leo@demo.com	Software_Support	L1	Medium	Ms. Nair	vijethfernandes21@gmail.com	Medium
Mia	mia@demo.com	Software_Support	L2	Low	Ms. Nair	vijethfernandes21@gmail.com	Medium
Nathan	nathan@demo.com	Software_Support	L2	High	Ms. Nair	vijethfernandes21@gmail.com	High
Olivia	olivia@demo.com	Software_Support	L3	Medium	Ms. Nair	vijethfernandes21@gmail.com	High
Paul	paul@demo.com	Hardware_Support	L1	Low	Mr. Verma	verma@demo.com	Low
Quinn	quinn@demo.com	Hardware_Support	L1	High	Mr. Verma	verma@demo.com	Medium
Rachel	rachel@demo.com	Hardware_Support	L2	Low	Mr. Verma	verma@demo.com	Medium
Sam	sam@demo.com	Hardware_Support	L2	Medium	Mr. Verma	verma@demo.com	Medium
Tina	tina@demo.com	Hardware_Support	L3	Low	Mr. Verma	verma@demo.com	High
Uma	uma@demo.com	Cloud_Ops	L1	Low	Mr. Reddy	reddy@demo.com	Low
Victor	victor@demo.com	Cloud_Ops	L1	Medium	Mr. Reddy	reddy@demo.com	Medium
Wendy	wendy@demo.com	Cloud_Ops	L2	Low	Mr. Reddy	reddy@demo.com	Medium
Xander	xander@demo.com	Cloud_Ops	L2	High	Mr. Reddy	reddy@demo.com	High
Yara	yara@demo.com	Cloud_Ops	L3	Medium	Mr. Reddy	reddy@demo.com	High
Zoe	zoe@demo.com	Cloud_Ops	L3	Low	Mr. Reddy	reddy@demo.com	Medium
Jhon	jhon@demo.com	Procurement	L3	Low	Mr. Tom	tom@demo.com	Medium
"""

# Convert text data to DataFrame
df = pd.read_csv(StringIO(DATA), sep="\t")

# Save to Excel
df.to_excel("roster_with_skills.xlsx", index=False)

print("Excel file 'roster_with_skills.xlsx' created successfully!")