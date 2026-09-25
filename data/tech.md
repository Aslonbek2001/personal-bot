# Web and APIs

## HTTP request lifecycle
- DNS resolution
- TCP and TLS handshake
- Request and response structure
- Server side: from load balancer to handler
- Where latency comes from

## HTTP methods, status codes and headers
- Safe and idempotent methods
- Status code families (2xx-5xx)
- Important headers: auth, caching, content type
- Choosing the right status code

## JSON and data serialization
- JSON structure and data types
- Serialization and deserialization
- Schema validation and API contracts
- JSON vs Protobuf vs MessagePack

## REST API design
- Resources and URL design
- Versioning strategies
- Idempotency and safe retries
- Error format and pagination

## API types compared
- REST
- GraphQL
- gRPC
- WebSocket and Server-Sent Events
- Webhooks
- How to choose

## Authentication and authorization
- Authentication vs authorization
- Sessions and cookies
- JWT: structure and trade-offs
- OAuth 2.0 flows
- Roles and permissions (RBAC)

## API gateway and traffic control
- What an API gateway does
- Rate limiting algorithms
- Pagination: offset vs cursor
- CORS

# Clean code and design

## Clean Code
- Meaningful names
- Small functions with one job
- Comments vs self-explaining code
- Code smells

## SOLID part 1: SRP and OCP
- Single Responsibility Principle
- Open/Closed Principle
- A real refactoring example
- When SOLID is overkill

## SOLID part 2: LSP, ISP, DIP
- Liskov Substitution Principle
- Interface Segregation Principle
- Dependency Inversion Principle

## DRY, KISS, YAGNI and separation of concerns
- DRY and the cost of a wrong abstraction
- KISS
- YAGNI
- Separation of concerns

## Dependency injection
- The problem DI solves
- Constructor injection
- DI containers
- DI and testing

## Creational patterns
- Factory
- Builder
- Singleton and why it is risky

## Structural patterns
- Adapter
- Facade
- Decorator
- Proxy

## Behavioral patterns
- Strategy
- Observer
- Command
- Chain of Responsibility

## Repository and Unit of Work
- Repository pattern
- Unit of Work
- Transaction boundaries
- When not to use them

# Backend architecture

## Layered architecture
- Presentation layer
- Service layer
- Data access layer
- Dependency direction between layers

## Clean and Hexagonal Architecture
- The domain at the center
- Ports and adapters
- Use cases
- Folder structure in a real project

## Monolith vs modular monolith vs microservices
- Monolith
- Modular monolith
- Microservices
- How to choose and when to split

## Sync vs async communication
- Request-response
- Message queues
- Event-driven architecture
- Delivery guarantees

## Databases
- SQL vs NoSQL
- Indexes
- Transactions and ACID
- Isolation levels
- The N+1 query problem

## Caching
- Where to cache
- Cache-aside
- TTL and invalidation
- Cache stampede

## Concurrency in backends
- Async I/O and the event loop
- Threads and the GIL
- Processes and workers
- Choosing a model for a workload

## Background jobs and task queues
- Why background jobs
- Task queue architecture
- Retries and dead-letter queues
- Scheduling

## Observability
- Structured logging
- Metrics
- Distributed tracing
- Alerts that matter

## Testing strategy
- Unit tests
- Integration tests
- End-to-end tests
- The test pyramid
- Test doubles: mocks, stubs, fakes

## Containers and delivery
- Docker images and layers
- CI/CD pipeline stages
- Environments: dev, staging, prod
- Configuration and secrets

## Scalability and reliability
- Vertical vs horizontal scaling
- Load balancing
- Retries, timeouts and backoff
- Circuit breaker
- Graceful degradation

# ML foundations

## The ML lifecycle
- Data collection and labeling
- Training
- Evaluation
- Deployment and monitoring

## Learning types and generalization
- Supervised learning
- Unsupervised learning
- Overfitting and underfitting
- Train, validation and test split

## Evaluation metrics
- Accuracy and its trap
- Precision and recall
- F1 score
- Choosing a metric for the business

## Embeddings
- What an embedding is
- How embedding models are trained
- Similarity measures
- Choosing an embedding model

## Transformers and LLMs
- Tokens and tokenization
- Attention (high level)
- Context window
- Temperature and sampling

## Model serving
- Batch vs real-time inference
- Latency and throughput
- GPU vs CPU serving
- Cost control

# RAG

## RAG architecture end to end
- Ingestion pipeline
- Retrieval step
- Generation step
- Where each part lives in production

## Document loading and chunking
- Loading different formats
- Chunk size and overlap
- Semantic and structure-aware chunking
- Metadata

## Vector databases and similarity search
- How a vector database stores data
- Exact vs approximate search (ANN)
- The HNSW index
- Metadata filtering

## Hybrid search and re-ranking
- BM25 keyword search
- Combining keyword and vector results
- Cross-encoder re-ranking

## Prompt construction and context management
- Prompt template structure
- Ordering and citing chunks
- Fitting the context window

## RAG evaluation
- Retrieval metrics: recall@k and MRR
- Faithfulness and groundedness
- Hallucinations
- Building an evaluation set

## Advanced RAG
- Query rewriting
- Multi-hop retrieval
- Agentic RAG

## Fine-tuning vs RAG vs prompt engineering
- What each approach changes
- Cost and effort
- A decision guide

# LLM applications

## Function calling and tool use
- How a model calls a tool
- Tool schemas
- The tool loop

## MCP (Model Context Protocol)
- Why MCP exists
- Hosts, clients and servers
- Tools, resources and prompts
- Transport: stdio and HTTP
- The request flow step by step

## AI agents
- What makes a system an agent
- Planning
- Memory
- Failure modes and limits

## LLM apps in production
- Caching
- Guardrails
- Cost tracking
- Monitoring and feedback

## LLM security
- Prompt injection
- Secrets and data leakage
- Data privacy