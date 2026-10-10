// Skills the CV matcher looks for, grouped by IT field. Each entry: [display name, field, ...extra spellings].
// Spellings are matched as whole words, case-insensitively, except entries listed in CASE_SENSITIVE.
const SKILLS = [
  // Software Development
  ["Java", "Software Development"], ["Python", "Software Development"], ["JavaScript", "Software Development", "JS", "ecmascript"],
  ["TypeScript", "Software Development"], ["C#", "Software Development", "c sharp", "csharp"], ["C++", "Software Development", "cpp"],
  ["Go", "Software Development", "golang", "Go language", "Go (Golang)"], ["Rust", "Software Development"], ["Kotlin", "Software Development"], ["Swift", "Software Development"],
  ["PHP", "Software Development"], ["Ruby", "Software Development", "ruby on rails", "Rails"], ["Scala", "Software Development"],
  [".NET", "Software Development", "dotnet", "asp.net", ".net core"], ["Spring Boot", "Software Development", "Spring", "spring framework"],
  ["Node.js", "Software Development", "nodejs", "node js", "express.js", "expressjs"], ["React", "Software Development", "react.js", "reactjs"],
  ["Next.js", "Software Development", "nextjs"], ["Angular", "Software Development", "angularjs"], ["Vue.js", "Software Development", "vue", "vuejs", "nuxt"],
  ["HTML", "Software Development", "html5"], ["CSS", "Software Development", "css3", "sass", "tailwind", "tailwind css"],
  ["Django", "Software Development"], ["Flask", "Software Development"], ["FastAPI", "Software Development"],
  ["REST APIs", "Software Development", "REST", "restful", "rest api", "api development"], ["GraphQL", "Software Development"],
  ["Microservices", "Software Development", "microservice"], ["Android", "Software Development"], ["iOS", "Software Development"],
  ["Flutter", "Software Development", "Dart"], ["React Native", "Software Development"], ["Full Stack", "Software Development", "full-stack", "fullstack"],
  ["Frontend", "Software Development", "front-end", "front end"], ["Backend", "Software Development", "back-end", "back end"],
  ["Git", "Software Development", "github", "gitlab", "bitbucket"], ["OOP", "Software Development", "object oriented", "object-oriented"],
  ["Design Patterns", "Software Development"], ["Embedded", "Software Development", "embedded systems", "firmware", "rtos"],
  ["Kafka", "Software Development", "apache kafka"], ["RabbitMQ", "Software Development"], ["Redis", "Software Development"],
  // DevOps & Cloud
  ["AWS", "DevOps & Cloud", "amazon web services", "ec2", "S3", "Lambda", "cloudformation"], ["Azure", "DevOps & Cloud", "microsoft azure", "aks"],
  ["Google Cloud", "DevOps & Cloud", "gcp", "google cloud platform", "gke"], ["Oracle Cloud", "DevOps & Cloud", "OCI"],
  ["Docker", "DevOps & Cloud", "containers", "containerization"], ["Kubernetes", "DevOps & Cloud", "k8s", "openshift", "helm"],
  ["Terraform", "DevOps & Cloud", "infrastructure as code", "iac"], ["Ansible", "DevOps & Cloud"], ["Puppet", "DevOps & Cloud"], ["Chef", "DevOps & Cloud"],
  ["Jenkins", "DevOps & Cloud"], ["CI/CD", "DevOps & Cloud", "ci cd", "continuous integration", "continuous delivery", "continuous deployment", "github actions", "gitlab ci", "azure devops"],
  ["DevOps", "DevOps & Cloud"], ["DevSecOps", "DevOps & Cloud"], ["SRE", "DevOps & Cloud", "site reliability"],
  ["Prometheus", "DevOps & Cloud"], ["Grafana", "DevOps & Cloud"], ["ELK", "DevOps & Cloud", "elasticsearch", "logstash", "kibana", "elastic stack"],
  ["Datadog", "DevOps & Cloud"], ["Monitoring", "DevOps & Cloud", "observability"], ["Serverless", "DevOps & Cloud"],
  ["Bash", "DevOps & Cloud", "shell scripting", "shell script"], ["PowerShell", "DevOps & Cloud"], ["Cloud Architecture", "DevOps & Cloud", "cloud computing", "cloud migration"],
  // Cybersecurity
  ["Cybersecurity", "Cybersecurity", "cyber security", "information security", "infosec", "it security"], ["SOC", "Cybersecurity", "security operations"],
  ["SIEM", "Cybersecurity", "splunk", "qradar", "Sentinel", "arcsight"], ["Penetration Testing", "Cybersecurity", "pentest", "pentesting", "ethical hacking", "red team", "offensive security"],
  ["Vulnerability Management", "Cybersecurity", "vulnerability assessment", "nessus", "qualys"], ["Incident Response", "Cybersecurity", "dfir", "digital forensics", "forensics"],
  ["Threat Intelligence", "Cybersecurity", "threat hunting"], ["Firewalls", "Cybersecurity", "firewall", "fortigate", "palo alto", "checkpoint", "check point", "ngfw"],
  ["IAM", "Cybersecurity", "identity and access management", "identity management", "okta", "sailpoint", "active directory"], ["PAM", "Cybersecurity", "privileged access", "cyberark"],
  ["SASE", "Cybersecurity", "zero trust", "ztna"], ["Application Security", "Cybersecurity", "appsec", "owasp", "sast", "dast"], ["Cloud Security", "Cybersecurity"],
  ["GRC", "Cybersecurity", "governance risk and compliance", "grc framework"], ["ISO 27001", "Cybersecurity", "iso27001", "nist", "pci dss", "pci-dss"],
  ["CISSP", "Cybersecurity"], ["CEH", "Cybersecurity"], ["OSCP", "Cybersecurity"], ["CompTIA Security+", "Cybersecurity", "security+"], ["CISM", "Cybersecurity"],
  ["EDR", "Cybersecurity", "crowdstrike", "endpoint security", "xdr"], ["OT Security", "Cybersecurity", "ics security", "scada"], ["Encryption", "Cybersecurity", "pki", "cryptography"],
  // Data & AI
  ["SQL", "Data & AI", "t-sql", "pl/sql", "plsql"], ["PostgreSQL", "Data & AI", "postgres"], ["MySQL", "Data & AI"], ["SQL Server", "Data & AI", "mssql"],
  ["Oracle Database", "Data & AI", "oracle db"], ["MongoDB", "Data & AI", "nosql"], ["Data Engineering", "Data & AI", "data engineer", "data pipelines", "data pipeline"],
  ["ETL", "Data & AI", "elt", "informatica", "ssis"], ["Spark", "Data & AI", "apache spark", "pyspark"], ["Hadoop", "Data & AI", "Hive"],
  ["Airflow", "Data & AI", "apache airflow"], ["dbt", "Data & AI"], ["Snowflake", "Data & AI"], ["Databricks", "Data & AI"], ["BigQuery", "Data & AI"],
  ["Data Warehousing", "Data & AI", "data warehouse", "data lake", "lakehouse"], ["Power BI", "Data & AI", "powerbi"], ["Tableau", "Data & AI"],
  ["Business Intelligence", "Data & AI"], ["Data Analysis", "Data & AI", "data analytics", "data analyst", "analytics"], ["Excel", "Data & AI", "advanced excel"],
  ["Machine Learning", "Data & AI", "ML"], ["Deep Learning", "Data & AI", "neural networks"], ["AI", "Data & AI", "artificial intelligence"],
  ["Generative AI", "Data & AI", "genai", "gen ai", "llm", "llms", "large language models", "RAG", "prompt engineering"], ["NLP", "Data & AI", "natural language processing"],
  ["Computer Vision", "Data & AI", "opencv"], ["TensorFlow", "Data & AI", "keras"], ["PyTorch", "Data & AI"], ["scikit-learn", "Data & AI", "sklearn"],
  ["Pandas", "Data & AI", "numpy"], ["MLOps", "Data & AI", "mlflow", "kubeflow"], ["Statistics", "Data & AI", "statistical"], ["R", "Data & AI", "r programming", "rstudio", "r language"], ["Data Governance", "Data & AI"],
  // QA & Testing
  ["Software Testing", "QA & Testing", "qa", "quality assurance", "manual testing"], ["Test Automation", "QA & Testing", "automation testing", "automated testing"],
  ["Selenium", "QA & Testing"], ["Cypress", "QA & Testing"], ["Playwright", "QA & Testing"], ["Appium", "QA & Testing"], ["JUnit", "QA & Testing", "testng", "pytest", "jest"],
  ["Performance Testing", "QA & Testing", "jmeter", "load testing", "loadrunner"], ["API Testing", "QA & Testing", "postman", "rest assured"], ["ISTQB", "QA & Testing"],
  // Networking & Telecom
  ["Networking", "Networking & Telecom", "computer networks", "network engineering"], ["TCP/IP", "Networking & Telecom", "tcp ip"], ["Routing", "Networking & Telecom", "bgp", "ospf", "eigrp"],
  ["Switching", "Networking & Telecom", "vlan", "vlans"], ["Cisco", "Networking & Telecom", "ccna", "ccnp", "ccie"], ["Juniper", "Networking & Telecom", "jncia", "jncip"],
  ["SD-WAN", "Networking & Telecom", "sdwan"], ["MPLS", "Networking & Telecom"], ["Wireless", "Networking & Telecom", "wi-fi", "wifi", "wlan"], ["VoIP", "Networking & Telecom", "SIP"],
  ["5G", "Networking & Telecom"], ["LTE", "Networking & Telecom", "4g"], ["RAN", "Networking & Telecom", "radio access network", "RF"], ["Telecom", "Networking & Telecom", "telecommunications"],
  ["Load Balancing", "Networking & Telecom", "f5", "load balancer"], ["DNS", "Networking & Telecom", "dhcp"],
  // Systems & Infrastructure
  ["Linux", "Systems & Infrastructure", "unix", "red hat", "rhel", "ubuntu", "centos"], ["Windows Server", "Systems & Infrastructure", "windows administration"],
  ["VMware", "Systems & Infrastructure", "vsphere", "esxi", "virtualization", "hyper-v"], ["System Administration", "Systems & Infrastructure", "sysadmin", "system administrator"],
  ["Storage", "Systems & Infrastructure", "SAN", "NAS", "netapp"], ["Backup", "Systems & Infrastructure", "veeam", "disaster recovery"], ["Data Center", "Systems & Infrastructure", "data centre", "datacenter"],
  ["Microsoft 365", "Systems & Infrastructure", "office 365", "o365", "exchange", "intune", "sccm"], ["Patch Management", "Systems & Infrastructure"], ["Middleware", "Systems & Infrastructure", "weblogic", "websphere", "tomcat"],
  ["Database Administration", "Systems & Infrastructure", "dba"],
  // ERP & Business Apps
  ["SAP", "ERP & Business Apps", "sap s/4hana", "s/4hana", "sap hana"], ["ABAP", "ERP & Business Apps"], ["Oracle ERP", "ERP & Business Apps", "oracle ebs", "oracle fusion", "e-business suite"],
  ["Microsoft Dynamics", "ERP & Business Apps", "dynamics 365", "d365"], ["Salesforce", "ERP & Business Apps", "Apex", "Lightning"], ["ServiceNow", "ERP & Business Apps"],
  ["IFS ERP", "ERP & Business Apps", "ifs cloud", "ifs applications"], ["Workday", "ERP & Business Apps"], ["ERP", "ERP & Business Apps"], ["CRM", "ERP & Business Apps"],
  // IT Support
  ["IT Support", "IT Support", "technical support", "help desk", "helpdesk", "service desk", "desktop support"], ["ITIL", "IT Support", "itsm"],
  ["Troubleshooting", "IT Support"], ["Jira Service Management", "IT Support", "remedy", "zendesk"], ["Hardware", "IT Support", "hardware support"],
  // Product & Project
  ["Agile", "Product & Project", "scrum", "kanban", "SAFe"], ["Project Management", "Product & Project", "pmp", "prince2"], ["Product Management", "Product & Project", "product owner", "product manager"],
  ["Business Analysis", "Product & Project", "business analyst", "requirements gathering", "cbap"], ["Jira", "Product & Project", "confluence"], ["Stakeholder Management", "Product & Project"],
  // UI/UX
  ["UI/UX", "UI/UX Design", "UI", "UX", "user experience", "user interface", "ux design", "ui design"], ["Figma", "UI/UX Design", "Sketch", "adobe xd"],
  ["Wireframing", "UI/UX Design", "prototyping", "wireframes"], ["User Research", "UI/UX Design", "usability testing"],
  // Architecture
  ["Solution Architecture", "Architecture", "solutions architect", "solution architect"], ["Enterprise Architecture", "Architecture", "togaf", "enterprise architect"],
  ["System Design", "Architecture", "distributed systems", "scalability"],
];

// Spellings that only count when written with exactly this capitalisation (they are also ordinary words).
const EXACT_CASE = new Set(["AI", "ML", "UI", "UX", "SOC", "PAM", "IAM", "RAN", "RF", "SAN", "NAS", "SIP", "SAFe", "CRM", "ERP", "GRC", "QA",
  "REST", "RAG", "JS", "OCI", "SRE", "ELK", "CSS", "HTML", "SQL", "ETL", "CEH", "EDR", "PHP", "OOP", "DNS", "LTE", "MPLS", "ITIL", "IAM", "CISM",
  "Lambda", "Sentinel", "Dart", "Spring", "Rails", "Sketch", "Lightning", "Apex", "Hive", "S3", "Go", "Rust", "Swift", "Chef", "Puppet", "Ruby",
  "Scala", "Spark", "Flask", "Storage", "Backup", "Hardware", "Monitoring", "Excel", "Statistics", "Wireless", "Routing", "Switching", "Embedded",
  "Agile", "Encryption", "Workday", "Jira", "Git", "Bash", "Android", "Angular", "React", "Kafka", "Redis", "Docker", "Azure", "Selenium", "Cypress"]);
// Display names that are too ambiguous to search for on their own (their other spellings are used instead).
const NOT_A_SPELLING = new Set(["Go", "R"]);
