# Assignments

## Week 3: Build Your Single Agent + Add External Tools

This week you'll build a single AI agent in Azure AI Foundry and extend it with external tools.

**Start here**: [Single Agent Architecture](single_agent_architecture.md) — Understand the problem and architecture before diving into the labs.

### Deliverables

| Component | Points |
|-----------|--------|
| Architecture diagram + brief reasoning | 15 pts |
| **Choose one:** | |
| → Create a Logic App and connect it to your agent | 10 pts |
| → Create an Azure Function and connect it to your agent | 15 pts |

**Total: 25-30 points** (depending on choice)

### Option A: Logic App (10 pts)

Build a Logic App workflow and connect it to your agent via HTTP.

| Step | Lab |
|------|-----|
| 1. Build your Logic App | [Lab 2: Logic Apps](../notebooks/lab2_logic_apps.ipynb) |
| 2. Connect to your agent | [Lab 3: Single Agent + HTTP Tools](../notebooks/lab3_single_agent_tool_calling.ipynb) |

### Option B: Azure Function (15 pts)

Build an Azure Function and connect it to your agent. You can choose **either** integration approach:

| Approach | Description | Labs |
|----------|-------------|------|
| **HTTP Tool** | Direct HTTP calls from agent to function | [Lab 1](../notebooks/lab1_azure_functions.ipynb) → [Lab 3](../notebooks/lab3_single_agent_tool_calling.ipynb) |
| **MCP Server** | Standardized MCP protocol with auto-discovery | [Lab 4](../notebooks/lab4_mcp_server_azure_functions.ipynb) → [Lab 5](../notebooks/lab5_single_agent_mcp_integration.ipynb) |

### HTTP vs MCP: Which Should I Choose?

| HTTP Tool | MCP Server |
|-----------|------------|
| Simpler to understand | Industry-standard protocol |
| Direct HTTP calls | Auto-discovery of tools |
| One tool per endpoint | Multiple tools per server |
| Good for learning basics | Better for production systems |

Both approaches use Azure Functions — the difference is *how* your agent connects to them.

### What to Submit

1. **Architecture diagram** — Show your agent, tools, and how they connect
2. **Brief reasoning** — Why did you choose this approach? What are the benefits?
3. **Working demo** — Screenshot or recording of your agent using the tool


## Week 4: Multi-Agent Orchestration

This week you'll extend your Week 3 single agent into a **multi-agent system** using orchestration patterns from the Microsoft Agent Framework.

**Start here**: [Lab 6: Multi-Agent Orchestration](../notebooks/lab6_multi_agent_orchestration.ipynb) — Learn the 5 orchestration patterns before starting the assignment.

### Deliverables

| Component | Points |
|-----------|--------|
| Architecture diagram showing multi-agent topology | 10 pts |
| Pattern choice justification | 10 pts |
| Working multi-agent implementation | 10 pts |

**Total: 30 points**

### Your Task

Take the **tools you built in Week 3** and create a **multi-agent system** that uses them more effectively.

#### What You Have from Week 3

| Tool | Type | What It Does |
|------|------|--------------|
| `get_student_grades` | Local function | Query student grade data |
| `get_upcoming_deadlines` | Local function | Query assignment deadlines |
| `send_email_notification` | Logic App | Send email via workflow |
| `analyze_data` | Azure Function | Perform data analysis |

#### What You'll Build

Transform your single agent into **specialized agents** working together:

| Agent | Specialization | Tools |
|-------|----------------|-------|
| **Data Agent** | Data retrieval and analysis | `get_student_grades`, `get_upcoming_deadlines`, `analyze_data` |
| **Communication Agent** | Notifications and messaging | `send_email_notification` |
| **Advisor Agent** | Synthesizes insights, gives advice | Uses other agents' outputs |

### Choose Your Pattern

Based on what you learned in Lab 6, pick the orchestration pattern that fits:

| Pattern | When to Use for This Task |
|---------|---------------------------|
| **Sequential** | Data Agent → Advisor Agent → Communication Agent (pipeline) |
| **Concurrent** | Get grades AND deadlines simultaneously (parallel data) |
| **Group Chat** | Agents discuss student situation iteratively |
| **Handoff** | Advisor triages, hands off to Data or Communication as needed |
| **Custom (WorkflowBuilder)** | When none of the above fit your needs |

### What to Submit

1. **Architecture diagram** — Show your agents, their specializations, and how they connect
2. **Pattern justification** — 
    1. **Why multi-agent?** What limitation of your Week 3 single agent does this solve?
    2. **Pattern choice**: Why did you pick this orchestration pattern over the others?
    3. **Trade-offs**: What are the downsides of your multi-agent approach?
    4. **Real-world**: Where would you use this pattern in a production system?
3. **Working implementation** (Optional) — Code/video that demonstrates your multi-agent system

---