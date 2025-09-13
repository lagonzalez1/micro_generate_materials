# 📝 Assessment Materials Generator (RabbitMQ + PostgreSQL + Bedrock + S3)

This project implements a **Python RabbitMQ consumer** that automates the generation of **teaching materials** to support client-created assessments.

The workflow:

1. **Client** requests materials for a specific assessment (e.g., *Addition & Subtraction Workshop*).  
2. **RabbitMQ consumer** listens for requests on a queue.  
3. Consumer parses the request, **retrieves relevant assessment data from PostgreSQL**.  
4. Uses **Amazon Bedrock LLM models** to generate contextual supporting materials (lesson guides, activities, practice problems, etc.).  
5. Packages the results into structured **JSON**.  
6. Uploads the JSON file to **Amazon S3**.  
7. Returns a **presigned S3 URL** so the client can download and process the materials.

---


## 📂 Project Structure
.
├── Config/
│   ├── Client.py
│   ├── RabbitMQ.py
│   └── PostgresClient.py
├── Models/
│   ├── AmazonModel.py
│   ├── GeminiModel.py
│   └── test
├── Prompt/
│   ├── Prompt.py
│   ├── Prompts.py
├── main.py  
├── Dockerfile
├── Makefile
├── Requirements.txt 
└── README.md


## ⚙️ Architecture
+———+         +———––+         +—————–+         +–––––+
|  Client |  —>   |   RabbitMQ  |  —>   |   Consumer      |  —>   (Python script) |     Amazon Model ->    |  (JSON)  |  S3
+———+         +———––+         +—————–+         +–––––+

---

## 🔧 Setup

### 1. Requirements

- Python 3.9+
- RabbitMQ server
- PostgreSQL (with assessments table/data)
- AWS account with S3 + Bedrock enabled

Install dependencies:

```bash
pip install -r requirements.txt

```


## 🔧 Setup

### 2. Env 
# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_QUEUE=generate_materials

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=assessments_db
DB_USER=myuser
DB_PASS=mypassword

# AWS
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
S3_BUCKET=assessment-materials

GEMINI_API_KEY="APIKEY"
MODEL_ID="APIKEY"

## Running
```bash
    python main.py
```
or
OPTIONAL:
include postgreSQL image, RabbitMQ image in docker file to build and run
```bash
    docker run build .
```

## Example payload from rabbitMQ
{
    S3OutputKey    *string `json:"s3_output_key"`
    OrganizationID *int64  `json:"organization_id"`
    AssessmentId   *int64  `json:"assessment_id"`
    BiasType       *string `json:"bias_type"`
}

