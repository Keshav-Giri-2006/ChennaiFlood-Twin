# ChennaiFlood-Twin — AWS Deployment & Cloud Architecture

## 1. Purpose

This document defines the **AWS cloud deployment strategy** for ChennaiFlood-Twin.

Read this together with:

```text
00_PROJECT_CONTEXT.md
01_PRODUCT_REQUIREMENTS.md
02_ARCHITECTURE.md
03_DATA_AND_GIS.md
04_SWMM_MODEL.md
05_BACKEND_DESIGN.md
06_API_CONTRACT.md
07_FRONTEND_DESIGN.md
08_CESIUM_DIGITAL_TWIN.md
```

This document covers:

- AWS architecture,
- service responsibilities,
- local-to-cloud transition,
- frontend hosting,
- backend hosting,
- SWMM execution,
- object storage,
- databases,
- networking,
- IAM,
- environment configuration,
- observability,
- security,
- deployment,
- cost control,
- and academic-project practicality.

The AWS architecture must remain **cloud-native without becoming unnecessarily complicated**.

---

# 2. Cloud Objective

The target architecture is:

```text
USER
 │
 ▼
CloudFront
 │
 ├───────────────┐
 ▼               ▼
S3 Frontend     API
                 │
                 ▼
              Backend
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
       S3      SWMM     Database
     Results   Worker
        │        │
        └────┬───┘
             ▼
        Processed Results
             │
             ▼
          Frontend
```

The exact AWS services can evolve.

The architectural principle should remain:

> **Static web assets, API processing, simulation execution, persistent data, and large spatial results should have separate responsibilities.**

---

# 3. Cloud Deployment Philosophy

The project should support:

```text
LOCAL DEVELOPMENT
       ↓
LOCAL INTEGRATION
       ↓
AWS STAGING
       ↓
AWS DEMO / PRODUCTION
```

Do not make AWS mandatory for day-to-day development.

The same application should work locally first.

---

# 4. Local-First Rule

During development:

```text
React/Vite
   ↓
FastAPI
   ↓
local SWMM executable
   ↓
local project data
```

AWS is introduced after the local workflow works.

This reduces debugging complexity.

---

# 5. Target AWS Stack

A practical target stack is:

```text
Frontend:
Amazon S3
CloudFront

API:
Amazon ECS/Fargate
or another managed container runtime

Simulation:
ECS/Fargate worker
or dedicated worker compute

Storage:
Amazon S3

Database:
Amazon RDS PostgreSQL
or Amazon Aurora PostgreSQL

Networking:
Amazon VPC

Security:
IAM
Security Groups
Secrets Manager

Observability:
CloudWatch

DNS/TLS:
Route 53
ACM
```

Not every service must be deployed on day one.

---

# 6. Recommended MVP Cloud Architecture

For the academic MVP, prefer:

```text
S3
CloudFront
ECS/Fargate
S3
PostgreSQL
CloudWatch
IAM
Secrets Manager
```

Avoid introducing:

```text
Kubernetes
EKS
multi-region architecture
service mesh
complex event buses
```

unless genuinely required.

---

# 7. Why S3

Amazon S3 should store:

- frontend build artifacts,
- source/processed GIS assets where appropriate,
- DEM assets,
- rainfall datasets,
- SWMM model templates,
- simulation outputs,
- flood spatial products,
- logs/artifacts that need persistence.

S3 is appropriate for large immutable or versioned files.

---

# 8. S3 Storage Separation

Use logical prefixes/buckets.

Example:

```text
s3://chennaiflood-twin-data/
├── raw/
├── processed/
├── models/
├── scenarios/
└── static-gis/

s3://chennaiflood-twin-results/
├── simulations/
└── comparisons/
```

A separate frontend bucket may be used:

```text
s3://chennaiflood-twin-frontend/
```

The exact bucket strategy can vary by environment.

---

# 9. S3 Environment Separation

Do not mix development and production data.

Preferred:

```text
dev/
staging/
prod/
```

either through separate buckets or clearly separated prefixes.

For an academic project, separate buckets are often clearer.

---

# 10. S3 Object Naming

Use predictable keys.

Example:

```text
simulations/{simulationId}/
    swmm/
    flood/
    risk/
    bottlenecks/
    recommendations/
    metadata.json
```

Example:

```text
simulations/7f8d.../flood/timeslices/2023-12-04T08-00-00Z.geojson
```

Do not let the frontend construct arbitrary S3 keys.

---

# 11. S3 Access Rule

The frontend should not receive unrestricted bucket credentials.

Use:

```text
public/static assets
```

or:

```text
backend-mediated access
```

or:

```text
short-lived signed URLs
```

as appropriate.

---

# 12. Frontend Hosting

Recommended:

```text
React/Vite build
      ↓
S3
      ↓
CloudFront
      ↓
Browser
```

The S3 bucket should contain the built application.

CloudFront provides:

- CDN delivery,
- HTTPS,
- caching,
- global edge delivery.

---

# 13. SPA Routing

If React routing is used, configure CloudFront/S3 so application routes resolve correctly.

For example:

```text
/dashboard
/simulation/123
```

must not incorrectly return an S3 404.

For a simple single-page MVP, minimal routing may avoid unnecessary complexity.

---

# 14. CloudFront

CloudFront should serve:

```text
HTML
JS
CSS
images
static assets
```

and optionally selected public spatial assets.

Do not use CloudFront as a substitute for the backend API architecture.

---

# 15. TLS

Production access should use:

```text
HTTPS
```

Use AWS Certificate Manager for certificates where applicable.

Do not deploy the public application using plain HTTP.

---

# 16. DNS

Optional but recommended:

```text
Route 53
```

Example conceptual domains:

```text
app.example.com
api.example.com
```

The actual domain is deployment-specific.

---

# 17. Backend Hosting

The FastAPI backend should run in a managed server environment.

Recommended:

> **Amazon ECS with Fargate**

Conceptually:

```text
Internet
   ↓
Load Balancer
   ↓
ECS/Fargate
   ↓
FastAPI
```

---

# 18. Why ECS/Fargate

Fargate provides:

- containerized deployment,
- no server management,
- easy Docker integration,
- predictable runtime,
- compatibility with Python/FastAPI.

It also provides a straightforward path from:

```text
local Docker
```

to:

```text
AWS container
```

---

# 19. Backend Container

The backend should be packaged as a Docker image.

Conceptually:

```text
Dockerfile
    ↓
Python environment
    ↓
FastAPI
    ↓
SWMM dependencies
    ↓
application code
```

Do not depend on manually configured server state.

---

# 20. Container Reproducibility

The container should explicitly define:

- Python version,
- dependencies,
- SWMM version/runtime,
- application configuration.

This prevents:

```text
works on my machine
```

problems.

---

# 21. SWMM Execution in AWS

SWMM should execute in a controlled backend/worker environment.

Preferred conceptual flow:

```text
API
 ↓
simulation job
 ↓
worker
 ↓
create isolated working directory
 ↓
download model/data
 ↓
run SWMM
 ↓
parse results
 ↓
generate flood products
 ↓
upload results to S3
 ↓
update simulation status
```

---

# 22. Do Not Run Arbitrary SWMM Commands

User input must not become arbitrary shell commands.

The backend should select:

```text
approved model
approved executable
approved parameters
```

from controlled configuration.

---

# 23. Simulation Isolation

Every simulation should have an isolated working area.

Example:

```text
/tmp/simulations/{simulationId}/
```

or an equivalent container-local directory.

Never allow concurrent simulations to overwrite:

```text
model.inp
report.rpt
output.out
```

from another simulation.

---

# 24. Worker Architecture

For the initial MVP, two approaches are acceptable.

### Approach A — API container executes simulation

```text
FastAPI
  ↓
SWMM
```

Advantages:

- simple,
- fast to implement.

Disadvantages:

- API process is occupied,
- less scalable.

### Approach B — Separate worker

```text
FastAPI
  ↓
Job queue
  ↓
Worker
  ↓
SWMM
```

Advantages:

- cleaner architecture,
- scalable,
- better isolation.

For the academic MVP, Approach A may be acceptable initially.

The architecture should not prevent later migration to workers.

---

# 25. Recommended Evolution

Start:

```text
FastAPI
  ↓
isolated SWMM subprocess
```

Then, if needed:

```text
FastAPI
  ↓
SQS
  ↓
ECS worker
  ↓
SWMM
```

Do not build SQS/ECS worker orchestration before the local simulation workflow is stable.

---

# 26. Job Queue Option

Amazon SQS is a good future option for:

```text
simulation jobs
```

Conceptually:

```text
POST /simulations
        ↓
SQS
        ↓
worker
        ↓
SWMM
```

The API can immediately return:

```text
202 Accepted
```

with:

```text
simulationId
```

---

# 27. Simulation Status Persistence

Simulation state should not live only in browser memory.

Persist:

```text
simulationId
scenarioId
modelVersion
status
createdAt
startedAt
completedAt
error
result locations
```

in the backend database.

---

# 28. PostgreSQL

Recommended relational database:

> PostgreSQL

Potential AWS implementation:

> Amazon RDS for PostgreSQL

Use it for metadata, not giant raster files.

---

# 29. Database Responsibilities

Store:

```text
scenarios
simulations
model versions
processing versions
simulation status
result metadata
risk records
bottleneck metadata
recommendation metadata
```

Large files remain in S3.

---

# 30. Do Not Store Large Spatial Files in PostgreSQL by Default

Avoid putting entire:

```text
GeoJSON
DEM
SWMM output
raster
```

objects into ordinary relational columns.

Use S3 for large artifacts.

PostgreSQL stores:

```text
metadata
references
indexes
relationships
```

---

# 31. PostGIS

PostGIS is optional.

It can be introduced if spatial querying becomes important.

For the initial MVP, it may not be necessary because:

```text
S3 + GeoJSON + backend processing
```

may be sufficient.

Do not introduce PostGIS merely because it is a GIS project.

---

# 32. Suggested Database Entities

Conceptually:

```text
Scenario
Simulation
ModelVersion
ResultProduct
RiskLocation
Bottleneck
Recommendation
```

Potential relationships:

```text
Scenario
   │
   └── Simulation
          │
          ├── ResultProduct
          ├── RiskLocation
          ├── Bottleneck
          └── Recommendation
```

---

# 33. ResultProduct

A result-product record may contain:

```text
productId
simulationId
type
timestamp
s3Key
contentType
processingVersion
createdAt
```

This lets the API locate large files without embedding them in the database.

---

# 34. Simulation Metadata Example

Conceptually:

```json
{
  "simulationId": "7f8d...",
  "scenarioId": "michaung-2023",
  "modelVersion": "ward176-hydraulic-reconstructed-v1",
  "processingVersion": "flood-processing-v1",
  "status": "COMPLETED"
}
```

---

# 35. IAM Principle

Follow:

> **Least privilege.**

Each AWS workload should receive only the permissions it needs.

For example:

```text
Frontend
→ no AWS secret credentials

API
→ read approved model/scenario objects
→ write simulation metadata/results

Worker
→ read model/scenario inputs
→ write results

Database
→ application access only
```

---

# 36. IAM Roles

Prefer:

```text
IAM roles
```

over hardcoded:

```text
AWS access keys
```

inside application code.

Never commit AWS credentials to Git.

---

# 37. Secrets Manager

Use AWS Secrets Manager for sensitive values such as:

```text
database credentials
API secrets
private service credentials
```

Do not put them in:

```text
source code
Dockerfile
frontend environment
Git
```

---

# 38. Environment Variables

Backend configuration may include:

```text
DATABASE_URL
S3_DATA_BUCKET
S3_RESULTS_BUCKET
AWS_REGION
SWMM_EXECUTABLE
MODEL_VERSION
PROCESSING_VERSION
```

Values are environment-specific.

---

# 39. Frontend Environment

Frontend may contain public-safe values such as:

```text
VITE_API_BASE_URL
VITE_CESIUM_ION_TOKEN
```

Never place:

```text
DATABASE_URL
AWS_SECRET_ACCESS_KEY
```

in frontend environment variables.

---

# 40. Networking

A production backend should be placed inside an AWS VPC.

Conceptually:

```text
Internet
   ↓
Load Balancer
   ↓
Private application subnet
   ↓
ECS/Fargate
   ↓
Private database
```

---

# 41. Database Network Security

RDS should not be publicly accessible in the normal production architecture.

Allow access only from the application workload/security group.

---

# 42. Security Groups

Conceptually:

```text
ALB
 ↓
ECS
 ↓
RDS
```

Only required ports should be open.

Do not expose:

```text
PostgreSQL 5432
```

to the entire internet.

---

# 43. NAT / Internet Access

If private worker containers need internet access to download packages/data, NAT may be required.

However, runtime simulations should preferably use project-controlled assets already stored in S3.

Avoid unnecessary external network dependency during simulation.

---

# 44. Availability

This is an academic prototype.

Do not over-engineer high availability.

A reasonable target:

```text
single AWS region
managed services
restartable containers
persistent S3 results
persistent DB metadata
```

Multi-region deployment is unnecessary for the MVP.

---

# 45. Region

Choose one AWS region close to the development/deployment audience and supported by the selected services.

The exact region is deployment configuration.

Do not hardcode region-specific assumptions into application logic.

---

# 46. CloudWatch

Use CloudWatch for:

- backend logs,
- worker logs,
- errors,
- basic metrics.

Useful application logs:

```text
simulation created
simulation started
simulation completed
simulation failed
result uploaded
API error
```

---

# 47. Logging Rule

Never log:

```text
passwords
AWS secrets
database credentials
private tokens
```

Be cautious with:

```text
full user input
signed URLs
internal filesystem paths
```

---

# 48. Simulation Observability

Each simulation should be traceable using:

```text
simulationId
```

Example log:

```text
simulationId=7f8d...
stage=SWMM_EXECUTION
status=RUNNING
```

This makes debugging much easier.

---

# 49. Metrics

Useful metrics:

```text
simulation duration
simulation success count
simulation failure count
API latency
result processing duration
S3 upload failures
```

Advanced observability can wait until the core system works.

---

# 50. Health Checks

The API should expose:

```text
GET /health
GET /health/ready
```

as defined in:

```text
06_API_CONTRACT.md
```

Container health checks should use the appropriate endpoint.

---

# 51. CI/CD

A practical pipeline can be:

```text
Git push
   ↓
Build
   ↓
Test
   ↓
Docker build
   ↓
Push image
   ↓
Deploy
```

For frontend:

```text
Build Vite
   ↓
Upload S3
   ↓
Invalidate CloudFront cache
```

The exact CI/CD provider is flexible.

---

# 52. GitHub Actions

GitHub Actions is a reasonable implementation option if the repository is hosted on GitHub.

Potential workflows:

```text
frontend.yml
backend.yml
```

Do not create complicated pipelines before local builds/tests are stable.

---

# 53. Container Registry

For ECS deployments, use:

> Amazon ECR

Flow:

```text
Docker image
   ↓
ECR
   ↓
ECS/Fargate
```

---

# 54. Docker Image Strategy

Prefer separate images when responsibilities differ:

```text
backend image
worker image
```

For a simple MVP, one image may initially contain both FastAPI and SWMM dependencies if execution remains inside the API container.

---

# 55. Versioning

Every deployment should be traceable to:

```text
application version
model version
processing version
```

Example:

```text
Application: 1.0.0
Model: ward176-hydraulic-reconstructed-v1
Processing: flood-processing-v1
```

---

# 56. Model Artifact Management

The approved SWMM model should be stored as a versioned artifact.

Example:

```text
models/
└── ward176-hydraulic-reconstructed-v1/
    └── ward176_baseline_final_candidate.inp
```

If the project later promotes the reconstructed candidate to another model version, create a new version rather than silently overwriting the old model.

---

# 57. Source Data Immutability

Raw source data should be treated as immutable.

Examples:

```text
GCC source GeoJSON
NASA rainfall CSV
Copernicus DEM
```

Processed derivatives can have separate versions.

---

# 58. Processing Versioning

Flood post-processing should have an explicit version.

Example:

```text
flood-processing-v1
```

If the algorithm changes:

```text
flood-processing-v2
```

This prevents confusion between old and new results.

---

# 59. Simulation Reproducibility

A simulation should record enough information to reproduce it:

```text
scenario
model version
processing version
parameters
application version
```

where relevant.

---

# 60. AWS Result Lifecycle

Recommended:

```text
POST /simulations
        ↓
create DB record
        ↓
run simulation
        ↓
generate results
        ↓
upload S3
        ↓
write ResultProduct metadata
        ↓
mark COMPLETED
```

Do not mark the simulation complete before required result products are ready.

---

# 61. Failure Recovery

If SWMM succeeds but S3 upload fails:

```text
simulation != COMPLETED
```

unless the system has a reliable recovery state.

Prefer explicit states such as:

```text
PROCESSING
```

until required artifacts are persisted.

---

# 62. Partial Results

Partial results may exist in S3.

The API should expose only products that are actually ready.

Do not tell the frontend:

```text
floodAvailable=true
```

when the flood asset has not finished uploading.

---

# 63. S3 Signed URLs

For large private result files:

```text
frontend
   ↓
API
   ↓
signed URL
   ↓
S3
```

The frontend should treat the signed URL as opaque.

Never expose long-lived AWS credentials.

---

# 64. CORS

Production CORS should permit only the actual frontend origin(s).

Development can allow:

```text
localhost
```

as required.

Do not leave unrestricted CORS enabled in production.

---

# 65. CloudFront Caching

Good candidates:

```text
static JS
CSS
images
static GIS assets
completed immutable simulation products
```

Do not aggressively cache:

```text
simulation status
```

while it is changing.

---

# 66. Cache Invalidation

When deploying a new frontend:

```text
upload build
 ↓
CloudFront invalidation
```

Content-hashed Vite assets can reduce invalidation requirements.

---

# 67. Cost Philosophy

This is a student academic project.

Optimize for:

```text
working system
+
reasonable AWS cost
```

not:

```text
maximum enterprise architecture
```

---

# 68. Cost-Control Rules

Prefer:

- one region,
- modest ECS resources,
- small RDS instance where appropriate,
- S3 lifecycle policies,
- limited log retention,
- no unnecessary always-on workers,
- no Kubernetes,
- no multi-region replication.

---

# 69. Simulation Cost

SWMM simulations are CPU workloads.

Do not run large numbers of simulations continuously.

For a demo:

```text
one scenario
→ one simulation
→ cached results
```

is sufficient.

---

# 70. Result Reuse

If the same:

```text
scenario
+
model version
+
parameters
```

has already been simulated, consider reusing the existing result.

This reduces:

- compute,
- time,
- cost.

---

# 71. Simulation Cache Key

Conceptually:

```text
hash(
  scenarioId,
  modelVersion,
  parameters,
  processingVersion
)
```

If the hash matches an existing completed simulation, results may be reused.

---

# 72. AWS MVP vs Full Architecture

## MVP

```text
S3
CloudFront
ECS/Fargate
RDS
CloudWatch
IAM
Secrets Manager
```

## Future

```text
SQS
dedicated workers
autoscaling
PostGIS
advanced caching
more scenario types
```

The project should not depend on future components for the MVP.

---

# 73. Local → AWS Mapping

| Local | AWS |
|---|---|
| React/Vite | S3 + CloudFront |
| FastAPI | ECS/Fargate |
| Local files | S3 |
| SQLite/dev DB | PostgreSQL/RDS |
| SWMM executable | Containerized SWMM runtime |
| `/tmp/simulations` | Container temporary storage |
| Result files | S3 |
| `.env` | Secrets Manager / environment config |
| console logs | CloudWatch |

---

# 74. Local Filesystem Rule

The current Windows path:

```text
F:\ChennaiFlood-Twin\
```

must never be embedded in production code.

Use configurable paths locally.

Use:

```text
S3
+
container-local temporary directories
```

in AWS.

---

# 75. Windows Compatibility

Development currently occurs on Windows.

The application should not depend on:

```text
Windows-only shell commands
Windows path separators
hardcoded drive letters
```

Use Python path handling such as:

```python
pathlib.Path
```

and environment configuration.

---

# 76. SWMM Portability

The SWMM runtime must be packaged/configured so the same model can run in the AWS environment.

Test:

```text
local SWMM
```

and:

```text
container SWMM
```

with the same `.inp`.

The goal is reproducible model execution.

---

# 77. Container Temporary Storage

SWMM can write:

```text
.inp
.rpt
.out
```

to temporary container storage.

After processing:

```text
required artifacts
      ↓
S3
```

Temporary files should be cleaned up.

---

# 78. Data Download Strategy

At simulation start:

```text
S3 input
   ↓
temporary working directory
```

Do not repeatedly download unchanged static data for every individual request if it can be safely cached.

---

# 79. Static Data Packaging

For the academic MVP, some small static assets may be packaged into the container.

However, large datasets should generally remain in S3.

Use a clear distinction between:

```text
application code
```

and:

```text
data artifacts
```

---

# 80. Deployment Environments

Recommended:

```text
development
staging
production/demo
```

For a student project, staging and production may be combined if necessary.

Do not create many environments merely for appearance.

---

# 81. Configuration Separation

Environment-specific values include:

```text
AWS region
bucket names
database URL
API domain
Cesium token
model version
processing version
logging level
```

Keep them outside source code.

---

# 82. Production Startup

A production deployment should:

1. start container,
2. initialize configuration,
3. connect required services,
4. expose health endpoint,
5. become ready,
6. receive API traffic.

Do not run expensive model preparation on every container startup.

---

# 83. Database Migrations

If PostgreSQL is used, schema migrations should be version-controlled.

Possible tool:

```text
Alembic
```

Do not manually edit production tables as the normal deployment mechanism.

---

# 84. Backup

At minimum:

```text
S3 → durable result storage
RDS → managed backups
```

For the academic MVP, elaborate disaster recovery is unnecessary.

---

# 85. Disaster Recovery

The project does not require multi-region disaster recovery.

Reasonable expectation:

```text
source code in Git
raw/processed data in S3
simulation metadata in RDS
deployment configuration documented
```

A new environment should be reconstructable.

---

# 86. Security Baseline

The cloud deployment must:

- use HTTPS,
- use IAM roles,
- avoid hardcoded credentials,
- protect the database,
- validate API inputs,
- isolate simulation processes,
- avoid arbitrary shell execution,
- avoid public writable buckets,
- keep secrets out of frontend code.

---

# 87. Input Validation

Validate:

```text
scenarioId
modelVersion
parameters
timestamps
simulationId
```

before processing.

Do not allow arbitrary:

```text
S3 keys
filesystem paths
shell commands
```

from the client.

---

# 88. API Security Boundary

The frontend is untrusted.

Assume a malicious user can modify requests.

Therefore backend must independently validate:

```text
scenario
model
parameters
asset IDs
```

---

# 89. File Security

Never allow an API request to directly specify:

```text
../../etc/passwd
```

or equivalent path traversal.

Use IDs that map to controlled server-side paths/keys.

---

# 90. Resource Limits

Simulation requests should have sensible limits for:

```text
runtime
memory
request size
result size
```

The exact values can be tuned during deployment.

---

# 91. Timeout Handling

A simulation should not run forever.

Use:

```text
controlled timeout
```

and transition to:

```text
FAILED
```

with an appropriate error code if exceeded.

---

# 92. Concurrent Simulations

The MVP may restrict concurrent simulations.

Example:

```text
one active simulation per environment
```

or:

```text
small worker concurrency
```

This is preferable to allowing unlimited expensive jobs.

---

# 93. AWS Demo Reliability

Before the final presentation:

```text
pre-run the simulation
verify results
verify S3 assets
verify frontend
```

If possible, keep a completed simulation cached.

The live "Run Simulation" feature can still be demonstrated, but the project should not depend on an unpredictable cold start.

---

# 94. Cold Start Strategy

If simulation startup takes significant time:

```text
show preparation status
```

Do not pretend the model is running when it is actually waiting for infrastructure.

---

# 95. AWS Architecture Diagram

The final presentation architecture can be simplified to:

```text
                         USER
                          │
                          ▼
                    CloudFront
                     /       \
                    /         \
                   ▼           ▼
              S3 Frontend    API
                               │
                               ▼
                         ECS/Fargate
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
              S3 Data        SWMM           RDS
                              Worker
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                         S3 Results
                               │
                               ▼
                         Digital Twin
```

This is sufficient for the academic architecture discussion.

---

# 96. AWS Service Responsibilities

| Service | Responsibility |
|---|---|
| S3 | data/results/static assets |
| CloudFront | frontend delivery |
| ECS/Fargate | API and/or simulation workers |
| RDS PostgreSQL | application metadata |
| ECR | container images |
| VPC | network isolation |
| IAM | permissions |
| Secrets Manager | secrets |
| CloudWatch | logs/metrics |
| Route 53 | DNS |
| ACM | TLS certificates |
| SQS | optional simulation queue |

---

# 97. What Not to Use Initially

Do not introduce:

```text
EKS
Lambda for long SWMM simulations
DynamoDB as the default relational metadata store
OpenSearch
ElastiCache
multi-region architecture
complex event-driven microservices
```

unless an actual requirement emerges.

---

# 98. Why Not Lambda for SWMM

SWMM simulation and spatial post-processing may be long-running/CPU-intensive.

A containerized worker is a more straightforward fit.

Do not force the entire simulation pipeline into a serverless function merely because AWS Lambda exists.

---

# 99. Why Not Kubernetes

The project does not need:

```text
service orchestration at large scale
```

ECS/Fargate provides sufficient container orchestration with much less operational complexity.

---

# 100. AWS Data Flow

The cloud runtime should conceptually execute:

```text
USER
 ↓
CloudFront
 ↓
React
 ↓
API
 ↓
create Simulation
 ↓
retrieve Scenario
 ↓
prepare model
 ↓
run SWMM
 ↓
parse output
 ↓
flood processing
 ↓
risk processing
 ↓
bottleneck processing
 ↓
recommendations
 ↓
upload results to S3
 ↓
store metadata in RDS
 ↓
API response
 ↓
Cesium
```

---

# 101. AWS Deployment Order

Deploy in this order:

## Phase 1

```text
Dockerize backend
```

## Phase 2

```text
Test SWMM inside container
```

## Phase 3

```text
Create S3 buckets
```

## Phase 4

```text
Deploy backend
```

## Phase 5

```text
Deploy database
```

## Phase 6

```text
Connect simulation + S3
```

## Phase 7

```text
Deploy frontend
```

## Phase 8

```text
CloudFront
HTTPS
DNS
```

## Phase 9

```text
Observability
security
cost controls
```

---

# 102. AWS Testing Checklist

Before deployment:

```text
[ ] Backend Docker build works
[ ] SWMM runs inside container
[ ] Model file loads
[ ] Rainfall scenario loads
[ ] Simulation completes
[ ] Results upload to S3
[ ] Metadata saves to database
[ ] API returns simulation status
[ ] Flood product loads
[ ] Cesium loads spatial assets
[ ] HTTPS works
[ ] Frontend can call API
[ ] CORS works
[ ] Logs appear in CloudWatch
```

---

# 103. AWS Production Checklist

```text
[ ] No secrets in Git
[ ] No AWS keys in frontend
[ ] S3 write permissions restricted
[ ] RDS not public
[ ] HTTPS enabled
[ ] CORS restricted
[ ] API input validation enabled
[ ] Simulation timeout enabled
[ ] Temporary files cleaned
[ ] CloudWatch logging enabled
[ ] S3 lifecycle/cost controls considered
[ ] Model version recorded
[ ] Processing version recorded
```

---

# 104. Academic Demonstration Architecture

When explaining AWS during the project presentation:

### Frontend

```text
S3 + CloudFront
```

hosts the Digital Twin interface.

### Backend

```text
ECS/Fargate
```

runs the FastAPI services and controlled simulation workload.

### Storage

```text
S3
```

stores large GIS, rainfall, model, and simulation-result artifacts.

### Database

```text
RDS PostgreSQL
```

stores simulation metadata and structured application information.

### Security

```text
IAM + Secrets Manager + VPC
```

protect the application.

### Monitoring

```text
CloudWatch
```

provides logs and operational visibility.

---

# 105. Cost-Conscious Academic Deployment

A practical deployment strategy is:

```text
Development
→ local

Demo
→ AWS

After evaluation
→ stop/delete unnecessary compute resources
```

Persist required project artifacts in:

```text
Git
+
S3
```

and keep the cloud environment minimal.

---

# 106. Infrastructure as Code

Infrastructure as Code is recommended but optional for the first MVP.

Possible choices:

```text
Terraform
AWS CDK
CloudFormation
```

Do not introduce IaC complexity if the deployment cannot yet be reproduced manually.

Once stable, codify the infrastructure.

---

# 107. Deployment Documentation

The repository should eventually contain:

```text
docs/
└── deployment/
    ├── local.md
    ├── aws.md
    └── troubleshooting.md
```

These can be generated later.

---

# 108. Troubleshooting Categories

AWS troubleshooting should distinguish:

```text
Frontend
API
Container
SWMM
S3
Database
Network
Cesium
```

Do not debug all layers simultaneously.

---

# 109. AWS Failure Isolation

If:

```text
S3 works
RDS works
SWMM fails
```

the application should identify:

```text
simulation failure
```

rather than reporting:

```text
system unavailable
```

where possible.

---

# 110. Result Integrity

A result should only be exposed as complete when:

```text
SWMM completed
+
required post-processing completed
+
required S3 assets exist
+
metadata is stored
```

---

# 111. Scientific Provenance in Cloud

Each simulation should retain:

```text
scenarioId
modelVersion
processingVersion
applicationVersion
```

This is especially important when multiple deployments produce results.

---

# 112. Cloud Architecture vs Scientific Model

AWS does not make the model scientifically more accurate.

The cloud architecture provides:

```text
scalability
storage
availability
deployment
```

The scientific validity still comes from:

```text
data
+
assumptions
+
hydraulic model
+
validation
```

Do not claim AWS itself improves hydraulic accuracy.

---

# 113. Cloud Architecture vs Digital Twin

AWS supports the Digital Twin by providing:

```text
persistent data
+
simulation execution
+
API delivery
+
scalable result serving
```

Cesium provides the visualization.

SWMM provides hydraulic simulation.

The cloud is the infrastructure connecting these components.

---

# 114. Final Cloud Architecture

The recommended complete architecture is:

```text
                         ┌─────────────────┐
                         │      USER       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   CloudFront    │
                         └───────┬─────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             ┌──────────────┐         ┌──────────────┐
             │ S3 Frontend  │         │ API Gateway/ │
             │ React Build  │         │ Load Balancer│
             └──────────────┘         └──────┬───────┘
                                             │
                                             ▼
                                      ┌──────────────┐
                                      │ ECS/Fargate  │
                                      │ FastAPI      │
                                      └──────┬───────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
                          ▼                  ▼                  ▼
                    ┌──────────┐       ┌──────────┐       ┌──────────┐
                    │    S3    │       │  SWMM    │       │   RDS    │
                    │ Data/    │       │ Worker   │       │PostgreSQL│
                    │ Results  │       └──────────┘       └──────────┘
                    └────┬─────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Flood/Risk/  │
                  │ Decision     │
                  │ Products     │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   CesiumJS   │
                  │ Digital Twin │
                  └──────────────┘

       Supporting:
       IAM + VPC + Secrets Manager + CloudWatch + ECR
```

---

# 115. Final Non-Negotiable Rules

1. Keep local development fully functional.
2. Containerize the backend.
3. Ensure SWMM works inside the deployment environment.
4. Use S3 for large data/results.
5. Use PostgreSQL for structured metadata.
6. Never expose AWS credentials to the frontend.
7. Use IAM roles instead of hardcoded AWS keys.
8. Keep RDS private in production.
9. Use HTTPS.
10. Validate all simulation inputs server-side.
11. Never allow arbitrary command execution.
12. Isolate each simulation working directory.
13. Record simulation/model/processing versions.
14. Do not mark results complete before required products exist.
15. Use CloudWatch for operational visibility.
16. Keep AWS architecture proportional to an academic project.
17. Do not introduce Kubernetes without a real need.
18. Do not force long SWMM workloads into Lambda.
19. Keep raw data immutable.
20. Version processed data and models.
21. Use signed URLs or backend-controlled access for private large assets.
22. Keep frontend secrets out of browser code.
23. Do not hardcode Windows filesystem paths.
24. Make local → AWS behaviour reproducible.
25. Optimize for reliability and demonstrability before cloud sophistication.

---

# 116. Final Principle

AWS should make ChennaiFlood-Twin **deployable, persistent, reproducible, and demonstrable**.

It should not turn a student Digital Twin into an unnecessarily complex enterprise platform.

The intended relationship is:

```text
AWS
 │
 ├── stores data
 ├── runs backend
 ├── executes simulation
 ├── stores results
 └── delivers services
          │
          ▼
       API
          │
          ▼
      CesiumJS
          │
          ▼
   Digital Twin
```

The cloud is the infrastructure.

The Digital Twin is the product.

The hydraulic model and data remain the scientific foundation.
