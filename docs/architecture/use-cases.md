# Use Case Scenarios

This document contains detailed PlantUML diagrams for various Swisper Core use cases, demonstrating the system's capabilities across different interaction patterns.

## Use Case 1: Knowledge Search

```plantuml
@startuml
== Use Case 1: Knowledge Search ==
actor User
participant "AI Assistant App" as App1
participant "AI Assistant Backend" as Backend1
participant "Prompt Preprocessor" as Pre1
participant "LLM (GPT-4o)" as LLM1

User -> App1 : "What is the capital of Switzerland?"
App1 -> Backend1 : Prompt
Backend1 -> Pre1 : Intent = Knowledge
Pre1 -> LLM1 : Direct query
LLM1 --> Pre1 : Answer
Pre1 --> Backend1 : Response
Backend1 --> App1 : Answer
App1 --> User : "The capital of Switzerland is Bern"
@enduml
```

## Use Case 2: Email Triage and Smart Reply

```plantuml
@startuml
== Use Case 2: Email Triage and Smart Reply ==
actor User
participant "AI Assistant App" as App2
participant "AI Assistant Backend" as Backend2
participant "Prompt Preprocessor" as Pre2
participant "Email Tool" as Email
participant "LLM (GPT-4o)" as LLM2

User -> App2 : "Check my emails and suggest replies"
App2 -> Backend2 : Prompt
Backend2 -> Pre2 : Intent = Email Management
Pre2 -> Email : Fetch emails
Email --> Pre2 : Email list
Pre2 -> LLM2 : Analyze and suggest replies
LLM2 --> Pre2 : Suggested replies
Pre2 --> Backend2 : Triage + suggestions
Backend2 --> App2 : Email summary + replies
App2 --> User : Show prioritized emails with suggested responses
@enduml
```

## Use Case 3: Email RAG Search

```plantuml
@startuml
== Use Case 3: Email RAG Search ==
actor User
participant "AI Assistant App" as App3
participant "AI Assistant Backend" as Backend3
participant "Prompt Preprocessor" as Pre3
participant "Email Tool" as Email3
participant "LLM (GPT-4o)" as LLM3

User -> App3 : "Find emails about project Alpha"
App3 -> Backend3 : Prompt
Backend3 -> Pre3 : Intent = Search
Pre3 -> Email3 : Search emails with RAG
Email3 --> Pre3 : Relevant emails
Pre3 -> LLM3 : Summarize findings
LLM3 --> Pre3 : Summary
Pre3 --> Backend3 : Search results + summary
Backend3 --> App3 : Organized results
App3 --> User : Show relevant emails with context
@enduml
```

## Use Case 4: Contract-Based Purchase (Graphics Card)

```plantuml
@startuml
== Use Case 4: Contract-Based Purchase (Graphics Card) ==
actor User
participant "AI Assistant App" as App4
participant "AI Assistant Backend" as Backend4
participant "Prompt Preprocessor" as Pre4
participant "Contract Engine" as Contract
participant "Google Shopping Tool" as Shop
participant "LLM (GPT-4o)" as LLM4

User -> App4 : "Find me the best RTX 4070 under 450 CHF"
App4 -> Backend4 : Prompt
Backend4 -> Pre4 : Intent = Purchase
Pre4 -> Contract : Start purchase contract
Contract -> Shop : Search product
Shop --> Contract : Product list
Contract -> LLM4 : Ask clarifying questions if needed
LLM4 --> Contract : User preference answers
Contract -> Shop : Refine search
Contract --> Backend4 : Best result
Backend4 --> App4 : Proposal
App4 --> User : Offer best product
@enduml
```

## Use Case 5: Complex Travel Booking

```plantuml
@startuml
== Use Case 5: Complex Travel Booking ==
actor User
participant "AI Assistant App" as App5
participant "AI Assistant Backend" as Backend5
participant "Prompt Preprocessor" as Pre5
participant "Contract Engine" as Contract5
participant "Travel Tool" as Travel
participant "LLM (GPT-4o)" as LLM5

User -> App5 : "Book a trip to Paris for next month"
App5 -> Backend5 : Prompt
Backend5 -> Pre5 : Intent = Travel Booking
Pre5 -> Contract5 : Start travel contract
Contract5 -> Travel : Search flights + hotels
Travel --> Contract5 : Options
Contract5 -> LLM5 : Present options and ask preferences
LLM5 --> Contract5 : User choices
Contract5 -> Travel : Book selected options
Travel --> Contract5 : Confirmation
Contract5 --> Backend5 : Booking details
Backend5 --> App5 : Trip confirmation
App5 --> User : Show complete itinerary
@enduml
```

## Architecture Benefits

These use cases demonstrate:

1. **Flexible Intent Routing**: Different user intents trigger appropriate processing paths
2. **Contract-Based Flows**: Complex multi-step processes managed by FSM contracts
3. **Tool Integration**: Seamless integration with external services and APIs
4. **Context Awareness**: Memory and session management across interactions
5. **User Experience**: Consistent interface across different interaction types

For implementation details, see:
- [Tools and Contract Management](tools-and-contracts.md)
- [Session Management](session-management.md)
- [Memory Management](memory-management.md)
