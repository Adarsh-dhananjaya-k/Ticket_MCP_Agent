import pandas as pd
from io import StringIO

ROSTER_DATA = """Name	Email	Team	Role	Workload	Manager	Manager_Email
Alice	alice@demo.com	SAP_Support	L2	High	Mr. Kumar	kumar@demo.com
Bob	bob@demo.com	SAP_Support	L2	Low	Mr. Kumar	kumar@demo.com
Charlie	charlie@demo.com	Database_Admin	L3	Medium	Ms. Sharma	sharma@demo.com
David	david@demo.com	Network_Ops	L1	Low	Mr. Patel	patel@demo.com
Eve	eve@demo.com	Network_Ops	L2	Low	Mr. Patel	patel@demo.com
Frank	frank@demo.com	Network_Ops	L1	Medium	Mr. Patel	patel@demo.com
Grace	grace@demo.com	Database_Admin	L2	Low	Ms. Sharma	sharma@demo.com
Henry	henry@demo.com	Database_Admin	L1	Medium	Ms. Sharma	sharma@demo.com
Irene	irene@demo.com	SAP_Support	L1	Low	Mr. Kumar	kumar@demo.com
Jack	jack@demo.com	SAP_Support	L3	Medium	Mr. Kumar	kumar@demo.com
Karen	vijethfernandes23@gmail.com	Software_Support	L1	Low	Ms. Nair	vijethfernandes21@gmail.com
Leo	leo@demo.com	Software_Support	L1	Medium	Ms. Nair	vijethfernandes21@gmail.com
Mia	mia@demo.com	Software_Support	L2	Low	Ms. Nair	vijethfernandes21@gmail.com
Nathan	nathan@demo.com	Software_Support	L2	High	Ms. Nair	vijethfernandes21@gmail.com
Olivia	olivia@demo.com	Software_Support	L3	Medium	Ms. Nair	vijethfernandes21@gmail.com
Paul	paul@demo.com	Hardware_Support	L1	Low	Mr. Verma	verma@demo.com
Quinn	quinn@demo.com	Hardware_Support	L1	High	Mr. Verma	verma@demo.com
Rachel	rachel@demo.com	Hardware_Support	L2	Low	Mr. Verma	verma@demo.com
Sam	sam@demo.com	Hardware_Support	L2	Medium	Mr. Verma	verma@demo.com
Tina	tina@demo.com	Hardware_Support	L3	Low	Mr. Verma	verma@demo.com
Uma	uma@demo.com	Cloud_Ops	L1	Low	Mr. Reddy	reddy@demo.com
Victor	victor@demo.com	Cloud_Ops	L1	Medium	Mr. Reddy	reddy@demo.com
Wendy	wendy@demo.com	Cloud_Ops	L2	Low	Mr. Reddy	reddy@demo.com
Xander	xander@demo.com	Cloud_Ops	L2	High	Mr. Reddy	reddy@demo.com
Yara	yara@demo.com	Cloud_Ops	L3	Medium	Mr. Reddy	reddy@demo.com
Zoe	zoe@demo.com	Cloud_Ops	L3	Low	Mr. Reddy	reddy@demo.com
Jhon	jhon@demo.com	Procurement	L3	Low	Mr. Tom	tom@demo.com
"""

# Convert string to dataframe
df = pd.read_csv(StringIO(ROSTER_DATA), sep="\t")

# Save to Excel
df.to_excel("roster.xlsx", index=False)

print("roster.xlsx created successfully")