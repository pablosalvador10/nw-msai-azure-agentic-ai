---
name: notebook-development
description: Helps create and structure Jupyter notebooks for teaching labs. Use this skill when creating lab notebooks, adding explanations for students, structuring educational content, or writing code cells with proper documentation.
---

# Notebook Development Skill (Teaching Labs)

## Overview

This skill helps create **well-structured Jupyter notebooks** for teaching Northwestern MS AI students about Azure services and agentic AI.

## Target Audience

- **Who**: Graduate students in MS AI program
- **Background**: Smart industry professionals, strong coding skills
- **Tone**: Professional, educational, explains *why* not just *how*
- **Level**: Intermediate to advanced Python, new to Azure/AI Foundry

## Notebook Structure Template

```
1. Title & Overview (Markdown)
   - Lab title
   - Learning objectives
   - Prerequisites
   - Architecture diagram

2. Setup & Prerequisites (Code + Markdown)
   - Import checks
   - Tool verification
   - Environment setup

3. Core Concepts (Markdown)
   - Explain the theory
   - Architecture diagrams
   - Key terminology tables

4. Step-by-Step Implementation (Code + Markdown)
   - One concept per section
   - Code cells with comments
   - Explanatory markdown between code

5. Testing & Verification (Code)
   - Test the implementation
   - Show expected outputs

6. Summary (Markdown)
   - Key takeaways table
   - Next steps
   - Additional resources
```

## Writing Style Guidelines

### Markdown Cells

```markdown
## Step X: Clear Action Title

**Why this matters:** Brief explanation of the concept's importance.

### Key Concepts

| Concept | Description |
|---------|-------------|
| Term 1  | Clear definition |
| Term 2  | Clear definition |

### Architecture

\`\`\`
┌─────────────┐     ┌─────────────┐
│  Component  │────▶│  Component  │
└─────────────┘     └─────────────┘
\`\`\`

Now let's implement this:
```

### Code Cells

```python
# Clear section comment explaining what this code does
# Include inline comments for non-obvious logic

def example_function(data: list[float]) -> dict:
    """
    Brief description of what the function does.

    Args:
        data: List of numbers to process

    Returns:
        Dictionary with computed statistics
    """
    # Validate input
    if not data:
        raise ValueError("Data cannot be empty")

    # Compute statistics
    result = {
        "count": len(data),
        "mean": sum(data) / len(data),
    }

    return result

# Test the function
sample_data = [10, 20, 30, 40, 50]
result = example_function(sample_data)
print(f"✅ Analysis complete: {result}")
```

## ASCII Art Diagrams

Use consistent styles for architecture diagrams:

### Flow Diagram
```
Input ───▶ Process ───▶ Output
```

### Component Diagram
```
┌─────────────────┐     ┌─────────────────┐
│   Component A   │────▶│   Component B   │
│   (description) │◀────│   (description) │
└─────────────────┘     └─────────────────┘
```

### Layered Architecture
```
┌─────────────────────────────────────────┐
│            Presentation Layer            │
├─────────────────────────────────────────┤
│             Business Logic              │
├─────────────────────────────────────────┤
│              Data Layer                 │
└─────────────────────────────────────────┘
```

## Emoji Conventions

Use emojis consistently:

| Emoji | Meaning |
|-------|---------|
| ✅ | Success/Complete |
| ❌ | Error/Failure |
| ⚠️ | Warning/Caution |
| 📝 | Note/Documentation |
| 🔧 | Configuration/Setup |
| 🎉 | Celebration/Milestone |
| 📡 | Network/API |
| 🔒 | Security |
| 💡 | Tip/Insight |

## Tables for Key Concepts

```markdown
| Feature | Description | Example |
|---------|-------------|---------|
| Feature 1 | Clear description | `code example` |
| Feature 2 | Clear description | `code example` |
```

## Code Output Formatting

```python
# Print structured output
print("=" * 50)
print("📊 Results Summary")
print("=" * 50)
print(f"  • Count: {result['count']}")
print(f"  • Mean:  {result['mean']:.2f}")
print("=" * 50)
```

## Prerequisites Check Pattern

```python
import subprocess
import shutil

def check_tool(name: str, command: list) -> bool:
    """Check if a tool is installed."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        version = result.stdout.strip().split('\n')[0]
        print(f"✅ {name}: {version}")
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print(f"❌ {name}: Not installed")
        return False

print("Checking required tools...\n")
tools = [
    ("Python", ["python", "--version"]),
    ("Azure CLI", ["az", "--version"]),
]
all_ok = all(check_tool(name, cmd) for name, cmd in tools)

if all_ok:
    print("\n🎉 All tools installed!")
else:
    print("\n⚠️ Some tools missing. See installation instructions above.")
```

## Summary Section Template

```markdown
## 🎯 Summary

### What You Built
Brief description of the complete implementation.

### Key Takeaways

| Concept | Implementation |
|---------|----------------|
| Concept 1 | How it was implemented |
| Concept 2 | How it was implemented |

### Next Steps
- Link to next lab
- Advanced topics to explore
- Additional resources

## 📚 Resources
- [Official Documentation](url)
- [Tutorial](url)
```
