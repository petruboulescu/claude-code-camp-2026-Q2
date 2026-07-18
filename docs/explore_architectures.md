# Explore Agent Architectures

This md documents explorations made on 0_preweek.md.

## 1. An agent file with referenced files eg. AGENT.md,  @~/docs/*.MD

The simplest agent architecture consists of a single agent instruction file, with optional references to additional files that are loaded conditionally when needed.

The first experiment should evaluate whether this minimal architecture can connect to the MUD and complete a simple, clearly defined goal, such as:

> Find the bakery and list the menu.

The experiment should begin with the smallest and least capable available model. More capable models should only be introduced if the simpler model cannot complete the task reliably.


### Technical Observations


    Using Haiku 4.5 we created a CLAUDE.md with a simple prompt, and told it will need to manage its own local memory via simple markdown 
files. We provided it with the location of the MUD and the players credentials.

    The agent struggled to connect to the MUD and everything degenerated into a shell script avalanche.Interestingly, separating the username 
and password into explicit fields caused additional confusion, and it attempted to use the password as the username.
    The agent did not have enough information about Text User Interface of the MUD to login and see its mistakes.
    Increasing the model intelligence to Sonnet 5 did help, but up to a point. The model was more efficient in his atempts to log in, but there 
was no persistent cnnection, so it was mostly an efficiency in brute forcing a text interface.

### Technical Conclusions

    A better prompt or an additional artifact describing the MUD's text interface could probably improve login performance. However, because 
the login flow is deterministic, it is more appropriate to handle it with a script rather than spend model tokens on a fixed sequence of 
actions.
    Markdown files may also be insufficient for representing complex player and world state. However, the experiment did not conclusively 
determine whether the coding harness's existing agentic loop could manage that state reliably.

## 2. Agent skills

    For this second part of our experiment, we created a MUD-specific skill containing a script for maintaining the connection and executing 
commands. The agent was also responsible for managing its own player and world state, by updating two given .md files

### Technical Observations

    Using Claude, we produced a skill that allowed Haiku 4.5 to connect to and interact with the MUD reliably. As mentioned in preweek file 
this is a success of the determinism, not of the architecture.

    The agent could complete simple, bounded goals, although often with a high number of calls. And here we need to pause and bring efficiency 
into discussion. Haiku is a cheap model, but having to do 90+ calls for a goal is probably not the way to go.

    However, it did not consider broader strategies such as gaining experience, improving the skill through other activities, or estimating 
what would be required to unlock another level.

    The limitations became clearer when the agent was given the broader goal of defeating the Massive Minotaur in the Newbie Zone- what's 
supposed to be the overarching "main goal". It located the Newbie Zone, but performed significant backtracking while searching for the target. When it could not find the Minotaur or open locked doors, it came back asking questions and remained overly literal and single-focused. Once told that the target was found with the Red Room, it concentrated on locating that exact room rather than preparing for the likely boss encounter.

A human player would normally retain the main objective while progressively exploring, training, collecting resources, and improving survivability. The agent instead treated the final objective as the immediate next action. I suspect the agent requires a way to break the tasks (similar to Claude plan's feature)

For example:

Goal: Defeat the Massive Minotaur in the Newbie Zone north of town.

Before leaving town, the agent should evaluate preparation:
Can useful information be collected from NPCs?
Are weapons, armour, food, or healing resources available?
Is additional training required? - e.g based on how much that character was played

While travelling, it should evaluate whether discoveries justify a detour:

Does the discovery contribute to the main goal?
Could it provide useful resources or experience?
Would ignoring it create unnecessary backtracking later?
Should it become a side objective?

This behaviour could be controlled through player preferences.

### Technical Conclusions

Agent Skills work well for adding domain-specific instructions and deterministic tools. The skill substantially improved connection reliability and enabled the agent to complete simple goals.

However, Skills alone do not solve planning, state management, route reasoning, or long-term goal execution.

A more capable implementation is documented in the preweek.md file

The player should also have a way to bring preferences into how the agent behaves. These would influence how the agent plans, explores, prepares, and responds to uncertainty.

When a goal is submitted, the system should expose its initial decomposition and current plan so that the reasoning process, progress, and changes in strategy can be reviewed.